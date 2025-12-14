# Deployment Guide for Upanishad AI

This guide explains how to deploy your FastAPI application to production. We recommend using **Render** or **Railway** for the easiest setup.

## Prerequisites
1.  **Push your code to GitHub**: Make sure your project is in a public or private GitHub repository.
2.  **Environment Variables**: Have your secrets (`GOOGLE_API_KEY`, `PINECONE_API_KEY`, `TWILIO_...`, etc.) ready.

---

## Option 1: Deploy on Render (Recommended)

Render offers a free tier for web services (though it spins down after inactivity).

1.  **Sign Up**: Go to [dashboard.render.com](https://dashboard.render.com/) and sign up/login with GitHub.
2.  **New Web Service**:
    *   Click **"New +"** -> **"Web Service"**.
    *   Select your repository `upnishad`.
3.  **Configure Settings**:
    *   **Name**: `upnishad-ai` (or whatever you like).
    *   **Region**: Choose one close to you (e.g., Singapore or Frankfurt).
    *   **Runtime**: **Python 3**.
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
        *   *Note: Render automatically sets the `PORT` env var, but usually expects 10000 if not specified.*
4.  **Environment Variables**:
    *   Scroll down to **"Environment Variables"**.
    *   Add each key-value pair from your `.env` file:
        *   `GOOGLE_API_KEY`: `...`
        *   `PINECONE_API_KEY`: `...`
        *   `PINECONE_INDEX_NAME`: `gita`
        *   `TWILIO_ACCOUNT_SID`: `...`
        *   `TWILIO_AUTH_TOKEN`: `...`
        *   `TWILIO_FROM_NUMBER`: `...`
        *   `WHATSAPP_TO_NUMBER`: `...`
5.  **Deploy**: Click "Create Web Service". Render will clone your repo, install dependencies, and start the server.

### Post-Deployment (Twilio Setup)
Once deployed, Render will give you a public URL (e.g., `https://upnishad-ai.onrender.com`).

1.  Go to your **Twilio Console** -> **Messaging** -> **WhatsApp Sandbox Settings**.
2.  Update the **"When a message comes in"** URL to:
    `https://upnishad-ai.onrender.com/api/whatsapp`
3.  Save. Now your WhatsApp bot works globally!

---

## Option 2: Deploy on Railway

Railway is another excellent option with a small trial credit.

1.  **Sign Up**: [railway.app](https://railway.app/).
2.  **New Project**: "Deploy from GitHub repo".
3.  Select your repo.
4.  **Variables**: Go to the "Variables" tab and add all your `.env` keys.
5.  **Start Command**: Go to "Settings" -> "Deploy" -> "Start Command" and enter:
    `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6.  Railway usually auto-detects everything else.

---

## Option 3: Docker (Advanced)

If you prefer using a container, create a `Dockerfile` in the root (already created below) and deploy the container to any cloud provider (AWS, Google Cloud Run, Azure).

### Dockerfile Content
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Option 4: Google Cloud Run (No CLI Required)

You can deploy directly from GitHub using the Google Cloud Console.

1.  **Push to GitHub**: Ensure your latest code (including the `Dockerfile`) is on GitHub.
2.  **Go to Cloud Run**: Open the [Google Cloud Console](https://console.cloud.google.com/run).
3.  **Create Service**: Click **"Create Service"**.
4.  **Deploy from Repository**:
    *   Click **"Continuously deploy from a repository"**.
    *   Click **"Setup Cloud Build"** and connect your GitHub account.
    *   Select your `upnishad` repository.
    *   Click **Next**.
5.  **Build Configuration**:
    *   Select **Dockerfile** as the build type.
    *   Source location: `/` (root directory).
6.  **Service Settings**:
    *   **Service Name**: `upnishad-ai`
    *   **Region**: Select a region (e.g., `us-central1` or `asia-south1` for Mumbai).
    *   **Authentication**: Select **"Allow unauthenticated invocations"**. This is required for Twilio to reach your API.
7.  **Environment Variables & Secrets**:
    *   Expand the **"Container, Networking, Security"** section.
    *   Go to the **"Variables & Secrets"** tab.
    *   Click **"Add Variable"** and add all your keys from `.env` (`GOOGLE_API_KEY`, `TWILIO_ACCOUNT_SID`, etc.).
8.  **Create**: Click "Create". Google Cloud will start building your container and deploy it.

### Post-Deployment
*   Copy the URL provided at the top of the service page (e.g., `https://upnishad-ai-uc.a.run.app`).
*   Update your **Twilio Sandbox** with this new URL + `/api/whatsapp`.

