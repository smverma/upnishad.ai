import os
from pinecone import Pinecone
from typing import List
from dotenv import load_dotenv

load_dotenv()

class PineconeInferenceEmbeddings:
    """Custom Embeddings wrapper for Pinecone Inference API (Reused for debug)."""
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

def debug_query(query: str):
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    if not (pinecone_api_key and index_name):
        print("Missing API keys.")
        return

    print(f"Debugging Query: '{query}'")
    
    # 1. Embed
    print("Generating embeddings...")
    embeddings = PineconeInferenceEmbeddings(api_key=pinecone_api_key)
    query_vector = embeddings.embed_query(query)
    
    if not query_vector:
        print("Failed to generate embeddings.")
        return

    # 2. Query Pinecone
    print(f"Querying Pinecone Index: {index_name}...")
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(index_name)
    
    results = index.query(
        vector=query_vector,
        top_k=5, 
        include_metadata=True,
        namespace="gita"
    )
    
    print(f"\nFound {len(results.matches)} matches:")
    for i, match in enumerate(results.matches):
        print(f"\n--- Match {i+1} (Score: {match.score:.4f}) ---")
        print(f"ID: {match.id}")
        if match.metadata:
            # Print text preview
            text = match.metadata.get('text', 'NO TEXT FOUND IN METADATA')
            print(f"Content Preview: {text[:500]}...") # Show first 500 chars
            print(f"Metadata: {match.metadata}")
        else:
            print("No metadata found.")

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    debug_query("what is karma")
