import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from fastapi import FastAPI, Request, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi_sso.sso.google import GoogleSSO
from app.rag.engine import ask_question, initialize_rag
from app.whatsapp.handler import handle_whatsapp_message
from app.youtube.automation import generate_daily_story
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Upanishad & Geeta AI")

# --- Authentication Setup ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Normally you'd want a specific secret key in env, but fallback for dev is okay
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-please-change") 
# Base URL should be set in env for prod, e.g. https://myapp.com
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Setup SSO
sso = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    sso = GoogleSSO(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=f"{BASE_URL}/auth/callback",
        allow_insecure_http=True # Allow http for localhost
    )

# Add Session Middleware (Required for storing user info)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG on startup
@app.on_event("startup")
async def startup_event():
    initialize_rag()
    if not sso:
        print("WARNING: Google SSO not initialized. check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")

# --- Auth Endpoints ---

@app.get("/auth/login")
async def login():
    if not sso:
        return {"error": "Google SSO not configured"}
    return await sso.get_login_redirect()

@app.get("/auth/callback")
async def callback(request: Request):
    if not sso:
        return {"error": "Google SSO not configured"}
    try:
        user = await sso.verify_and_process(request)
        # Store user in session
        request.session["user"] = {
            "email": user.email,
            "display_name": user.display_name,
            "picture": user.picture
        }
        return RedirectResponse(url="/")
    except Exception as e:
        print(f"Auth Error: {e}")
        return JSONResponse(status_code=500, content={"message": "Authentication failed"})

@app.get("/auth/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")

@app.get("/auth/me")
async def get_current_user(request: Request):
    user = request.session.get("user")
    if user:
        return {"authenticated": True, "user": user}
    return {"authenticated": False, "user": None}

# --- Core Attributes ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/ask")
def ask(question: str):
    try:
        # Optional: You can check auth here if you want to protect this endpoint
        # user = request.session.get("user")
        # if not user: raise HTTPException(...)
        
        answer = ask_question(question)
        return {"answer": answer}
    except Exception as e:
        print(f"CRITICAL ERROR in /api/ask: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"answer": f"Internal Server Error: {str(e)}"})

@app.post("/api/whatsapp")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    response = await handle_whatsapp_message(form_data)
    return response

@app.post("/api/trigger-daily-story")
async def trigger_story(background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_daily_story)
    return {"message": "Daily story generation triggered in background"}

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
