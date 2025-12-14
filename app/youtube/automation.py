import time
import os
from app.rag.engine import ask_question
from app.whatsapp.handler import send_whatsapp_message

def generate_daily_story():
    """
    Generates a daily wisdom story using Gemini and sends it to WhatsApp subscribers.
    """
    print("Generating daily story...")
    
    # Prompt the RAG system (Gemini)
    prompt = "Generate a very short, inspiring story (max 150 words) based on the Bhagavad Gita or Upanishads. End with a reflection question."
    
    story = ask_question(prompt)
    
    print(f"--- DAILY STORY ---\n{story}\n-------------------")
    
    # Send to WhatsApp
    # In a real app, retrieve subscribers from DB. 
    # Here we use a comma-separated list from ENV
    to_numbers_str = os.getenv("WHATSAPP_TO_NUMBER", "")
    
    if to_numbers_str:
        # Split by comma and strip whitespace
        recipients = [num.strip() for num in to_numbers_str.split(',') if num.strip()]
        
        for number in recipients:
            print(f"Sending daily story to {number}...")
            send_whatsapp_message(number, f"🌟 *Daily Vedic Wisdom* 🌟\n\n{story}")
    else:
        print("No WHATSAPP_TO_NUMBER defined. Story generated but not sent.")
    
    return story
