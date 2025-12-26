import uvicorn
import os
import sys

if __name__ == "__main__":
    print("STARTING FRESH UPNISHAD SERVER ON PORT 8001...")
    # Ensure we are running from the root directory
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    
    # Run Uvicorn on specific port 8001 to bypass any stuck processes on 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
