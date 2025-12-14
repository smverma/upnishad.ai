import requests
import sys

# Force utf-8 printing
sys.stdout.reconfigure(encoding='utf-8')

def test_api():
    url = "http://127.0.0.1:8000/api/ask"
    query = "what is karma"
    print(f"Testing API: {url} with query='{query}'")
    
    try:
        response = requests.post(url, params={"question": query})
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "No answer field")
            print("\nAPI Response Answer:")
            print("-" * 40)
            print(answer)
            print("-" * 40)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception calling API: {e}")

if __name__ == "__main__":
    test_api()
