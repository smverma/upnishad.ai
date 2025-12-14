import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.rag.engine import ask_question, initialize_rag
from app.whatsapp.handler import handle_whatsapp_message
from app.youtube.automation import generate_daily_story
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Upanishad & Geeta AI")

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

# API Endpoints
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/ask")
def ask(question: str):
    answer = ask_question(question)
    return {"answer": answer}

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
