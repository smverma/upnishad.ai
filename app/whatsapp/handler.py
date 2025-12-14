from fastapi import Request
from twilio.twiml.messaging_response import MessagingResponse
from app.rag.engine import ask_question
from twilio.rest import Client
import os

# Twilio Client for proactive messaging (Daily Story)
def get_twilio_client():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if account_sid and auth_token:
        return Client(account_sid, auth_token)
    return None

async def handle_whatsapp_message(form_data):
    """
    Handles incoming WhatsApp messages via Twilio webhook.
    """
    incoming_msg = form_data.get('Body', '').strip()
    sender = form_data.get('From', '') # e.g., 'whatsapp:+1234567890'
    
    print(f"Received message from {sender}: {incoming_msg}")

    # Get answer from RAG (Gemini + Pinecone)
    if incoming_msg:
        answer = ask_question(incoming_msg)
    else:
        answer = "I didn't catch that. Please ask a question about the Gita or Upanishads."

    # Create Twilio response
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(answer)

    return str(resp)

def send_whatsapp_message(to_number: str, body: str):
    """
    Sends a proactive WhatsApp message (e.g., daily story).
    Requires TWILIO_FROM_NUMBER (whatsapp:+14155238886 sandbox or your number).
    """
    client = get_twilio_client()
    from_number = os.getenv("TWILIO_FROM_NUMBER") # e.g. 'whatsapp:+14155238886'
    
    if not client or not from_number:
        print("Twilio credentials missing. Cannot send WhatsApp message.")
        return

    try:
        message = client.messages.create(
            from_=from_number,
            body=body,
            to=to_number
        )
        print(f"Message sent to {to_number}: {message.sid}")
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
