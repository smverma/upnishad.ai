import os
import time
import random
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone import Pinecone
from langchain_core.messages import HumanMessage
from typing import List

# Global variables
pinecone_index = None
llm = None
embeddings = None

class PineconeInferenceEmbeddings:
    """Custom Embeddings wrapper for Pinecone Inference API."""
    def __init__(self, api_key: str, model: str = "llama-text-embed-v2"):
        self.pc = Pinecone(api_key=api_key)
        self.model = model

    def embed_query(self, text: str) -> List[float]:
        try:
            response = self.pc.inference.embed(
                model=self.model,
                inputs=[text],
                parameters={"input_type": "query", "truncate": "END"}
            )
            return response.data[0]['values']
        except Exception as e:
            print(f"Error embedding query: {e}")
            return []

def initialize_rag():
    global pinecone_index, llm, embeddings
    
    # Check for keys
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    if not (pinecone_api_key and index_name and google_api_key):
        print("Missing API Keys (PINECONE or GOOGLE). RAG will not function.")
        return

    # Embeddings
    try:
        embeddings = PineconeInferenceEmbeddings(
            api_key=pinecone_api_key,
            model="llama-text-embed-v2"
        )
    except Exception as e:
        print(f"Failed to initialize PineconeEmbeddings: {e}")
        return

    # Pinecone Index
    try:
        pc = Pinecone(api_key=pinecone_api_key)
        pinecone_index = pc.Index(index_name)
    except Exception as e:
        print(f"Failed to connect to Pinecone Index: {e}")
        return
    
    # LLM - Gemini 1.5 Flash (Good free tier)
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0.7, google_api_key=google_api_key)
        print("RAG Initialized successfully with Pinecone & Gemini (Direct Mode).")
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")

def call_llm_with_retry(prompt_messages, max_retries=5):
    """Calls the LLM with exponential backoff for 429 errors."""
    delay = 2
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt_messages)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "resourceexhausted" in error_str:
                if attempt < max_retries - 1:
                    sleep_time = delay + random.uniform(0, 1)
                    print(f"Quota hit. Retrying in {sleep_time:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(sleep_time)
                    delay *= 2  # Exponential backoff
                else:
                    raise e
            else:
                raise e

from app.rag.faiss_engine import search_gita

def ask_question(query: str, mode: str = "chat") -> str:
    global pinecone_index, llm, embeddings
    
    # Initialize Core RAG components (always needed for LLM)
    if not (llm):
        initialize_rag()
    
    # Context Retrieval Strategy
    context_parts = []
    
    # 1. DEEP DIVE MODE: Prefer Local FAISS (Gita)
    if mode == "deep_dive":
        print(f"Deep Dive Mode: Attempting Local FAISS Search for '{query}'")
        try:
            faiss_results = search_gita(query, top_k=5)
            if faiss_results:
                print(f"FAISS found {len(faiss_results)} matches.")
                for res in faiss_results:
                     # Create rich context string including metadata
                     text = f"Source: {res['source']}\nSanskrit: {res['sanskrit']}\nMeaning: {res['text']}"
                     context_parts.append(text)
            else:
                print("FAISS returned 0 results. Falling back to Pinecone.")
        except Exception as e:
            print(f"FAISS Search Failed: {e}. Falling back to Pinecone.")

    # 2. STANDARD/FALLBACK: Pinecone (Cloud)
    # Only query pinecone if we don't have enough context from FAISS yet
    if not context_parts:
        if not (pinecone_index and embeddings):
             initialize_rag()
        
        if pinecone_index and embeddings:
            try:
                # Embed query
                query_vector = embeddings.embed_query(query)
                if query_vector:
                    # Query Pinecone
                    results = pinecone_index.query(
                        vector=query_vector,
                        top_k=5,
                        include_metadata=True,
                        namespace="gita"
                    )
                    
                    print(f"Pinecone Matches: {len(results.matches)}")
                    for match in results.matches:
                        if match.score < 0.1: continue
                        text_content = match.metadata.get('text') or match.metadata.get('chunk_text')
                        if text_content:
                            context_parts.append(text_content)
            except Exception as e:
                print(f"Pinecone Search Error: {e}")

    context = "\n\n".join(context_parts)
    if not context:
        context = "No specific scripture context found. Answer from general vedic knowledge."

    # 4. Prompt LLM for JSON response
    
    if mode == "deep_dive":
        system_instruction = """You are an AI guide trained on Indian philosophical texts (Bhagavad Gita, Principal Upanishads).
Your role is to explain philosophical ideas clearly and compassionately, without preaching, judgment, or superstition.
You must be calm, neutral, and reflective. Avoid fatalism, fear, or moral pressure.

MANDATORY ANSWER STRUCTURE (Follow EXACTLY):

**1️⃣ Direct Answer (TL;DR)**
2–3 lines. Clear and practical definition.

**2️⃣ Scriptural Grounding**
- Reference (e.g. Bhagavad Gita 3.5)
- Sanskrit Quote (e.g. "Na hi kaścit...")
- English Meaning

**3️⃣ Meaning & Interpretation**
- Modern explanation
- No mysticism, no moral judgement
- Clear philosophy (e.g. "Karma is not fate/punishment but cause and effect")

**4️⃣ Practical Application**
- One real-life example (Work, family, study, or inner life)
- How to apply this wisdom today.

**5️⃣ Reflection Prompt**
- One gentle, open-ended question for the user to think about.

**Optional Persona Lens** (Only if helpful)
- 👩‍💼 For a Working Professional / 🎓 For a Student (brief specific advice)

If any section cannot be fulfilled based on context, state: "This teaching offers reflection rather than direct instruction."
"""
        prompt = f"""{system_instruction}
            
CONTEXT FROM SCRIPTURES:
{context}

USER QUESTION: {query}

IMPORTANT: Return VALID JSON with these keys:
- "answer": A markdown formatted string containing the 5 sections above. Use bold headers with Emojis exactly as shown (e.g. **1️⃣ Direct Answer**).
- "follow_up_questions": List of 4 short relevant follow-up questions.
"""
    else:
        # Standard Chat Mode
        prompt = f"""You are an assistant answering questions about the Bhagavad Gita and Upanishads.
Use the following pieces of retrieved context to answer the question at the end.
If the answer is not in the context, say that you don't know, but answer from your general knowledge of the scriptures if possible.
Please provide a concise and clear answer (maximum 300 words).

IMPORTANT: You must return your response in purely VALID JSON format with no markdown formatting (no ```json blocks).
The JSON must have two keys:
1. "answer": The text of your answer.
2. "follow_up_questions": A list of 4 short, relevant follow-up questions based on the answer.

Context:
{context}

Question: {query}
"""
        
    # Use retry logic
    response = call_llm_with_retry([HumanMessage(content=prompt)])
    print("LLM Response received successfully.")
    
    # Clean response content to ensure it's valid JSON (remove markdown code blocks if any)
    content_str = response.content
    if isinstance(content_str, list):
        content_str = "".join([str(part) for part in content_str])
    
    clean_content = str(content_str).replace('```json', '').replace('```', '').strip()
    
    import json
    try:
        return json.loads(clean_content)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON from LLM: {response.content}")
        # Fallback for plain text response to avoid crashing
        return {"answer": str(response.content), "follow_up_questions": []}


    except Exception as e:
        print(f"Error processing request: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            return "I am receiving a lot of requests right now. Please try again in a minute. (Quota Exceeded)"
        return f"Error processing request: {str(e)}"
