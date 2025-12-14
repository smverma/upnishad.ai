# Upanishad & Geeta AI Wisdom App

This project is an AI-powered application that answers questions based on the Upanishads and Bhagavad Gita using a RAG (Retrieval-Augmented Generation) approach. It includes a WhatsApp interface for accessibility and a daily trigger to generate content for YouTube growth.

## Features

1.  **RAG-based Q&A**: Ask questions and get answers grounded in the scriptures.
2.  **WhatsApp Interface**: Interact with the bot via WhatsApp.
3.  **Daily Wisdom Trigger**: Automates the creation of a daily story/message from the scriptures to engage the audience (e.g., for YouTube Shorts or Community posts).
4.  **Web Interface**: A beautiful, responsive web UI to interact with the AI.

## Tech Stack

-   **Backend**: Python, FastAPI
-   **AI/RAG**: LangChain, ChromaDB (Vector Store), OpenAI/HuggingFace (Embeddings & LLM)
-   **WhatsApp**: Twilio API (or Meta Cloud API)
-   **YouTube**: YouTube Data API
-   **Frontend**: HTML, CSS, JavaScript

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Set up environment variables (API keys for OpenAI, Twilio, etc.) in a `.env` file.
3.  Run the server:
    ```bash
    uvicorn app.main:app --reload
    ```
