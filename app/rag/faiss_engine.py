import os
import pickle

# Global FAISS index and metadata
faiss_index = None
gita_metadata = []
model = None

DATA_FILE_PATH = "app/data/bhagavad_gita.csv" # Expected CSV location
INDEX_FILE_PATH = "app/data/gita_faiss.index"
METADATA_FILE_PATH = "app/data/gita_metadata.pkl"

def initialize_faiss():
    global faiss_index, gita_metadata, model
    
    # Lazy Imports
    import pandas as pd
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    
    # Initialize Embedding Model (lightweight)
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2') 
    except Exception as e:
        print(f"Failed to load SentenceTransformer: {e}")
        return

    # Check if index exists to load
    if os.path.exists(INDEX_FILE_PATH) and os.path.exists(METADATA_FILE_PATH):
        try:
            faiss_index = faiss.read_index(INDEX_FILE_PATH)
            with open(METADATA_FILE_PATH, 'rb') as f:
                gita_metadata = pickle.load(f)
            print("Loaded FAISS index locally.")
            return
        except Exception as e:
            print(f"Error loading existing FAISS index, rebuilding: {e}")

    # Build Index from CSV
    if os.path.exists(DATA_FILE_PATH):
        print(f"Building FAISS index from {DATA_FILE_PATH}...")
        try:
            df = pd.read_csv(DATA_FILE_PATH)
            
            # Create text to embed: "Chapter X Verse Y: [Sanskrit] [Meaning]"
            documents = []
            gita_metadata = []
            
            for _, row in df.iterrows():
                # Correct Mapping based on bhagavad_gita.csv columns
                # Columns: ,verse_number,verse_in_sanskrit,sanskrit_verse_transliteration,translation_in_english,meaning_in_english,...
                
                # verse_number usually looks like "Chapter 1, Verse 1"
                verse_ref = row.get('verse_number', 'Unknown')
                sanskrit = row.get('verse_in_sanskrit', '')
                translation = row.get('translation_in_english', row.get('meaning_in_english', ''))
                
                # Clean up verse ref if needed or use as is
                
                text_for_embedding = f"{verse_ref}: {translation}"
                
                documents.append(text_for_embedding)
                gita_metadata.append({
                    "chapter": verse_ref, # Storing full ref string as chapter for simplicity in display
                    "verse": "",
                    "sanskrit": sanskrit,
                    "translation": translation,
                    "full_text": text_for_embedding
                })
            
            # Embed
            embeddings = model.encode(documents)
            
            # Create FAISS Index
            dimension = embeddings.shape[1]
            faiss_index = faiss.IndexFlatL2(dimension)
            faiss_index.add(embeddings.astype('float32'))
            
            # Save
            faiss.write_index(faiss_index, INDEX_FILE_PATH)
            with open(METADATA_FILE_PATH, 'wb') as f:
                pickle.dump(gita_metadata, f)
                
            print(f"FAISS index built with {len(documents)} verses.")
            
        except Exception as e:
            print(f"Failed to build FAISS index: {e}")
    else:
        print(f"Gita CSV not found at {DATA_FILE_PATH}. transform_local_rag will likely fail.")

def search_gita(query: str, top_k: int = 3):
    global faiss_index, gita_metadata, model
    
    if not (faiss_index and model and gita_metadata):
        initialize_faiss()
        if not (faiss_index and model):
            return []

    # Embed Query
    query_vector = model.encode([query])
    
    # Search
    distances, indices = faiss_index.search(query_vector.astype('float32'), top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx != -1 and idx < len(gita_metadata):
            meta = gita_metadata[idx]
            results.append({
                "text": meta['full_text'],
                "sanskrit": meta['sanskrit'],
                "source": meta['chapter'], # Contains "Chapter X, Verse Y"
                "score": float(distances[0][i])
            })
            
    return results
