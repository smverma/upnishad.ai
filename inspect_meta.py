import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

def check_metadata():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    
    # Query blindly in "gita" namespace to get ANY record
    # We will generate a dummy vector (all zeros or random) just to find *something* or use list/fetch if we knew IDs.
    # Since we don't have valid IDs handy (rec802 might be one), let's query.
    
    print("Querying namespace 'gita' to inspect metadata structure...")
    dummy_vector = [0.1] * 1024
    
    results = index.query(
        vector=dummy_vector,
        top_k=1,
        include_metadata=True,
        namespace="gita"
    )
    
    if results.matches:
        match = results.matches[0]
        print(f"Found ID: {match.id}")
        print(f"Metadata Keys: {list(match.metadata.keys())}")
        print("Full Metadata:", match.metadata)
    else:
        print("No matches found even with dummy vector?")

if __name__ == "__main__":
    check_metadata()
