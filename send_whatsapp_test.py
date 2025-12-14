import os
import sys
from dotenv import load_dotenv

# Enable UTF-8 for windows console
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

load_dotenv()
sys.path.append(os.getcwd())

from app.whatsapp.handler import send_whatsapp_message
from app.rag.engine import ask_question, initialize_rag

def main():
    target_number = os.getenv("WHATSAPP_TO_NUMBER")
    if not target_number:
        print("Error: WHATSAPP_TO_NUMBER not found in .env")
        return

    query = "what is karma"
    print(f"Generating answer for: '{query}' (Targeting ~500 words)...")
    
    # Ensure RAG is initialized
    initialize_rag()
    
    answer = ask_question(query)
    print(f"\nGenerated Answer ({len(answer)} chars):\n{answer[:200]}...\n")
    
    recipients = [num.strip() for num in target_number.split(',') if num.strip()]
    
    for number in recipients:
        print(f"Sending to {number}...")
        send_whatsapp_message(number, answer)
    
    print("Send attempted to all recipients.")

if __name__ == "__main__":
    main()
