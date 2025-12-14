import requests
import urllib.parse

def simulate_incoming_whatsapp(message_body):
    url = "http://localhost:8000/api/whatsapp"
    
    # Twilio sends data as form-encoded, not JSON
    data = {
        "Body": message_body,
        "From": "whatsapp:+919867228892", # Simulating your number
        "To": "whatsapp:+14155238886"     # Simulating the sandbox number
    }
    
    print(f"Simulating sending message: '{message_body}' to {url}...")
    
    try:
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("\nSuccess! Server received and processed the message.")
            print("--- Server Response (Twilio TwiML) ---")
            print(response.text) # This contains the XML response Twilio would read
            print("--------------------------------------")
        else:
            print(f"\n❌ Error: Server returned status code {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to localhost:8000. Is the server running?")

if __name__ == "__main__":
    # You can change the question here
    question = "What is the meaning of life according to Gita?"
    simulate_incoming_whatsapp(question)
