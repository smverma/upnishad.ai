import os
import time
import random
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone import Pinecone
from langchain_core.messages import HumanMessage, SystemMessage
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
    
    # LLM - Gemini 1.5 Pro (Better instruction following)
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5, google_api_key=google_api_key)
        print("RAG Initialized successfully with Pinecone & Gemini Pro (Direct Mode).")
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
    
    mode_in = mode.strip().lower()
    
    # 1. DETERMINE MODE
    # Force Deep Dive for core philosophical concepts regardless of UI toggles
    keywords = ["deep dive", "structure", "karma", "dharma", "yoga", "moksha", "life", "death", "soul", "god"]
    is_deep_dive = (mode_in == "deep_dive") or any(k in query.lower() for k in keywords)

    # DEBUG LOGGING (PROOF OF LIFE)
    try:
        with open("server_debug_log.txt", "a") as f:
            f.write(f"Query: {query} | Mode: {mode_in} | IsDeepDive: {is_deep_dive} | Time: {time.time()}\n")
    except:
        pass

    if is_deep_dive:
        print(f"Executing Deep Dive Logic for query: '{query}'")
    else:
        print(f"Executing Standard Chat Logic for query: '{query}'")
    
    # 2. CONTEXT RETRIEVAL
    retrieved_sources = [] # New: Store as objects for JSON serialization
    
    # Attempt FAISS (Local)
    try:
        # We always try FAISS first for Gita related queries as it is faster and more precise
        faiss_results = search_gita(query, top_k=4)
        if faiss_results:
            print(f"FAISS found {len(faiss_results)} matches.")
            for res in faiss_results:
                    # Spec Section 4.3: "ALWAYS send compressed meaning"
                    retrieved_sources.append({
                        "source": "Bhagavad Gita",
                        "reference": res['source'],
                        "core_idea": res['text'] # This is the meaning/translation
                    })
    except Exception as e:
        print(f"FAISS Search Skipped/Failed: {e}")

    # Fallback/Augment with Pinecone (Cloud)
    # If FAISS provided nothing, or if we are in standard chat and want more breadth
    if not retrieved_sources:
        if not (pinecone_index and embeddings):
                initialize_rag()
        
        if pinecone_index and embeddings:
            try:
                query_vector = embeddings.embed_query(query)
                if query_vector:
                    results = pinecone_index.query(
                        vector=query_vector,
                        top_k=4,
                        include_metadata=True,
                        namespace="gita"
                    )
                    for match in results.matches:
                        if match.score < 0.1: continue
                        text_content = match.metadata.get('text') or match.metadata.get('chunk_text')
                        if text_content:
                            retrieved_sources.append({
                                "source": "Upanishads/Vedic Text",
                                "reference": "Chunk ID: " + match.id,
                                "core_idea": text_content
                            })
            except Exception as e:
                print(f"Pinecone Search Error: {e}")

    # Spec Section 4.3: Create Context Object
    context_object = {
        "question": query,
        "retrieved_sources": retrieved_sources
    }
    
    import json
    context_json_str = json.dumps(context_object, indent=2)

    # 3. CONSTRUCT MESSAGES & CALL LLM
    messages = []
    
    if is_deep_dive:
        # Spec Section 1 & 2 & 3
        system_instruction = """You are an AI guide trained on Indian philosophical texts (Bhagavad Gita, Principal Upanishads).

## 1. Role Definition
- Explain concepts clearly and precisely
- Use retrieved texts as authoritative grounding
- Maintain a calm, modern, non-religious tone
- Educate, not persuade
- You are NOT a guru, preacher, or motivational speaker.

## 2. Canonical Philosophical Position
- Default stance: **Advaita Vedanta (Upanishadic non-dualism)**
- Atman ≡ Brahman
- Separation arises from ignorance (avidya)
- Liberation is through understanding, not belief

## 3. Mandatory Answer Structure (PURE MARKDOWN)
Every answer MUST include these sections in order (use exact headers):

1. **Scriptural Grounding**
   - Use ONLY retrieved verses.
   - Quote the original Sanskrit Shloka (Devanagari).
   - Chapter + verse required.

2. **Meaning & Interpretation**
   - Modern explanation.
   - No devotional or poetic language.

3. **Practical Application**
   - One real-life implication.

4. **Reflection Prompt**
   - One neutral, open-ended question.

AFTER the reflection prompt, add a section called "Suggested Questions:" with 4 follow-up questions.
"""
        user_content = f"""
CONTEXT (JSON):
{context_json_str}

USER QUESTION: {query}

INSTRUCTION:
Answer in PURE MARKDOWN format. Do not use JSON output.
Follow the 5 headers exactly.
"""
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=user_content)
        ]
    else:
        # Standard Chat
        # Reconstruct simple string context for standard chat
        context_str = ""
        if retrieved_sources:
             context_str = "\n\n".join([f"Source: {r['source']} ({r['reference']})\nContent: {r['core_idea']}" for r in retrieved_sources])
        else:
             context_str = "No specific scripture context found."

        prompt = f"""You are an assistant answering questions about the Bhagavad Gita and Upanishads.
Use the following pieces of retrieved context to answer the question at the end.
Please provide a concise and clear answer (maximum 300 words).

Context:
{context_str}

Question: {query}

IMPORTANT: Return VALID JSON.
The JSON must have two keys:
1. "answer": The text of your answer.
2. "follow_up_questions": A list of 4 short, relevant follow-up questions based on the answer.
"""
        messages = [HumanMessage(content=prompt)]

    # Call LLM
    try:
        response = call_llm_with_retry(messages)
    except Exception as e:
        return {"answer": f"Error calling AI: {str(e)}", "follow_up_questions": []}

    # 4. PROCESS RESPONSE
    if is_deep_dive:
        answer_text = response.content
        
        # Debug tag to prove new logic ran
        # Debug tag removed as per user request
        # status_tag = f"\n\n_(Mode: Deep Dive | Context: {'Local FAISS' if retrieved_sources else 'Cloud/General'})_"
        # answer_text += status_tag
        
        # Extract Follow Ups
        follow_ups = []
        if "Suggested Questions:" in answer_text:
            parts = answer_text.split("Suggested Questions:")
            answer_text = parts[0].strip()
            lines = parts[1].strip().split('\n')
            follow_ups = [line.strip('- ').strip() for line in lines if line.strip()]
            
        return {
            "answer": answer_text,
            "follow_up_questions": follow_ups if follow_ups else ["What is Dharma?", "Explain Yoga", "Who is Krishna?"]
        }
    else:
        # Standard JSON parsing
        content_str = str(response.content)
        if isinstance(response.content, list):
             content_str = "".join([str(part) for part in response.content])
             
        clean_content = content_str.replace('```json', '').replace('```', '').strip()
        try:
            import json
            return json.loads(clean_content)
        except json.JSONDecodeError:
            return {"answer": clean_content, "follow_up_questions": []}
