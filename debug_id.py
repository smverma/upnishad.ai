import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

def debug_pinecone():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    if not (api_key and index_name):
        print("Missing Keys")
        return

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    # 1. Fetch the specific record user mentioned
    target_id = "rec802"
    print(f"Fetching ID: {target_id}...")
    fetch_response = index.fetch(ids=[target_id])
    
    if target_id in fetch_response.vectors:
        vec_data = fetch_response.vectors[target_id]
        print(f"SUCCESS: Found {target_id}")
        print(f"Vector Dimension: {len(vec_data.values)}")
        print(f"Metadata: {vec_data.metadata}")
        
        # 2. Try to generate a query vector with the assumed model
        print("\n--- Testing Embedding Generation ---")
        model_id = "llama-text-embed-v2"
        try:
            print(f"Generating embedding for 'Karma' using model: {model_id}")
            resp = pc.inference.embed(
                model=model_id,
                inputs=["Karma"],
                parameters={"input_type": "query"}
            )
            gen_vector = resp.data[0]['values']
            print(f"Generated Vector Dimension: {len(gen_vector)}")
            
            if len(gen_vector) != len(vec_data.values):
                print("CRITICAL MISMATCH: Generated dimension does not match stored dimension!")
            else:
                print("Dimensions match.")
                
        except Exception as e:
            print(f"Embedding generation failed: {e}")

    else:
        print(f"FAILED: Could not find ID {target_id} in index '{index_name}' (Default Namespace).")
        print("Checking Index Stats...")
        print(index.describe_index_stats())

if __name__ == "__main__":
    debug_pinecone()
