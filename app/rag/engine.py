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

def ask_question(query: str) -> str:
    global pinecone_index, llm, embeddings
    
    if not (pinecone_index and llm and embeddings):
        initialize_rag()
        if not (pinecone_index and llm and embeddings):
             # check which one is missing for better error
            missing = []
            if not os.getenv("PINECONE_API_KEY") or "your_" in os.getenv("PINECONE_API_KEY", ""): missing.append("PINECONE_API_KEY")
            if not os.getenv("PINECONE_INDEX_NAME") or "your_" in os.getenv("PINECONE_INDEX_NAME", ""): missing.append("PINECONE_INDEX_NAME")
            if not os.getenv("GOOGLE_API_KEY") or "your_" in os.getenv("GOOGLE_API_KEY", ""): missing.append("GOOGLE_API_KEY")
            
            if missing:
                return f"System not initialized. Missing or invalid real API keys in .env: {', '.join(missing)}"
            
            return "System not initialized. Check server logs."
    
    try:
        # 1. Embed query
        query_vector = embeddings.embed_query(query)
        if not query_vector:
            return "Failed to generate embeddings for query."

        # 2. Query Pinecone
        results = pinecone_index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True,
            namespace="gita"  # Correct namespace found in stats
        )
        
        # 3. Construct Context
        context_parts = []
        print(f"Query: {query}")
        print(f"Matches found: {len(results.matches)}")
        for match in results.matches:
            print(f" - Match ID: {match.id}, Score: {match.score}")
            # Similarity threshold (lowered to 0.1 to ensure we get data)
            if match.score < 0.1:
                print(f"   -> SKIPPED (Score < 0.1)")
                continue
                
            text_content = match.metadata.get('text') or match.metadata.get('chunk_text')
            
            if text_content:
                context_parts.append(text_content)
                print(f"   -> ADDED: {text_content[:100]}...")
            else:
                print(f"   -> SKIPPED (No 'text' or 'chunk_text'). Metadata keys: {list(match.metadata.keys()) if match.metadata else 'None'}")
        
        if not context_parts:
            print("No context parts after filtering.")
            print(f"Total Matches: {len(results.matches)}")
            if len(results.matches) > 0:
                print(f"First Match Metadata: {results.matches[0].metadata}")
            return "I couldn't find any relevant information in the scriptures to answer your question."

        context = "\n\n".join(context_parts)
        print(f"Start of LLM Context:\n{context[:500]}\nEnd of Context Preview")
        
        # 4. Prompt LLM
        prompt = f"""You are an assistant answering questions about the Bhagavad Gita and Upanishads.
Use the following pieces of retrieved context to answer the question at the end.
If the answer is not in the context, say that you don't know, but answer from your general knowledge of the scriptures if possible, explicitly stating it is from general knowledge.
Please provide a concise and clear answer (maximum 300 words).

Context:
{context}

Question: {query}
Answer:"""
        
        # Use retry logic
        response = call_llm_with_retry([HumanMessage(content=prompt)])
        print("LLM Response received successfully.")
        return response.content

    except Exception as e:
        print(f"Error processing request: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            return "I am receiving a lot of requests right now. Please try again in a minute. (Quota Exceeded)"
        return f"Error processing request: {str(e)}"
