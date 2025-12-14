import sys
import os

# Ensure we can print unicode on windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from dotenv import load_dotenv
load_dotenv()

# Add the current directory to sys.path so we can import app
sys.path.append(os.getcwd())

try:
    from app.rag.engine import ask_question, initialize_rag
except ImportError as e:
    print(f"Error importing app.rag.engine: {e}")
    print("Making sure we are running from project root.")
    sys.exit(1)

def main():
    query = "what is karma"
    print(f"Testing End-to-End RAG with query: '{query}'")
    
    # Initialize implementation
    print("Initializing RAG...")
    initialize_rag()
    
    print("Asking question...")
    response = ask_question(query)
    
    print("\n--- Final Response ---")
    print(response)

if __name__ == "__main__":
    main()
