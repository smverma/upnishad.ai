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
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.5, google_api_key=google_api_key)
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
    
    mode = mode.strip().lower() # Normalize mode string
    
    # Intent Detection Override
    # If the user explicitly asks for "deep dive" in the text, force the mode
    if "deep dive" in query.lower() or "structure" in query.lower():
        print(f"Intent detected in query ('{query}'). Forcing mode to 'deep_dive'.")
        mode = "deep_dive"

    print(f"RAG Engine processing: query='{query}', mode='{mode}'")
    
    # Context Retrieval Strategy
    context_parts = []

        # 1. DEEP DIVE MODE: Prefer Local FAISS (Gita)
    if mode == "deep_dive":
        print(f"Deep Dive Mode: Attempting Local FAISS Search for '{query}'")
        try:
            faiss_results = search_gita(query, top_k=3) # Reduce to 3 for focused context
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

    # ... (Pinecone fallback logic remains) ...
    
    context = "\n\n".join(context_parts)
    if not context:
        context = "No specific scripture context found. Answer from general vedic knowledge."

    # 4. Prompt LLM for JSON response
    
    messages = []
    
    if mode == "deep_dive":
        # Simplified System Instruction
        system_instruction = """You are a wise Vedic AI guide.
You must answer questions incorporating the provided scriptural context.

CRITICAL RULE:
You must strictly follow a specific 5-part structure for your answer.
Do not write a continuous paragraph. Use the exact headers below.

Structure:
1. **1️⃣ Direct Answer** (2 sentences max)
2. **2️⃣ Scriptural Grounding** (Quote the Sanskrit & English from context)
3. **3️⃣ Meaning & Interpretation** (Philosophical explanation)
4. **4️⃣ Practical Application** (Actionable advice)
5. **5️⃣ Reflection Prompt** (A question for the user)
"""
        # Reinforced User Content
        user_content = f"""
CONTEXT:
{context}

USER QUESTION: {query}

INSTRUCTION:
Based on the context above, answer the question using the 5 mandatory headers defined in your system instructions.
Return the result as valid JSON.
"""
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=user_content)
        ]
        print("Constructing Deep Dive Prompt with Dual-Enforcement.")

    else:
        # Standard Chat Mode (Add Mode Indicator)
        prompt = f"""You are an assistant answering questions about the Bhagavad Gita and Upanishads.
Use the following pieces of retrieved context to answer the question at the end.
Please provide a concise and clear answer (maximum 300 words).

Context:
{context}

Question: {query}

IMPORTANT: Return VALID JSON.
"""
        messages = [HumanMessage(content=prompt)]

        
    # Use retry logic
    response = call_llm_with_retry(messages)
    print("LLM Response received successfully.")
    
    # ... (Cleanup logic) ...

    import json
    try:
        final_json = json.loads(clean_content)
        
        # Debugging: Prepend mode to answer to confirm path
        status_tag = f"\n\n_(Mode: {mode} | Source: {'Local FAISS' if mode=='deep_dive' and context_parts else 'Pinecone/General'})_"
        
        if isinstance(final_json, dict) and "answer" in final_json:
             final_json["answer"] += status_tag
        
        return final_json
    except json.JSONDecodeError:
        print(f"Failed to parse JSON from LLM: {response.content}")
        # Fallback for plain text response to avoid crashing
        return {"answer": str(response.content), "follow_up_questions": []}


    except Exception as e:
        print(f"Error processing request: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            return "I am receiving a lot of requests right now. Please try again in a minute. (Quota Exceeded)"
        return f"Error processing request: {str(e)}"
