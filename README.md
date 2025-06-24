# ToonzyAI Backend

This service generates personalized cartoon avatars from text prompts using Vertex AI Imagen.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure Google Cloud:
   - Create a service account in Google Cloud Console
   - Download the service account key (JSON)
   - Save the key file in a secure location
   - Add the following to your `.env` file:
     ```bash
     # Google Cloud & Vertex AI
     GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
     VERTEX_PROJECT=extended-bongo-463404-r3
     VERTEX_LOCATION=us-central1
     
     # Database
     DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/toonzyai
     ```

3. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Features

- Text-to-image generation using Google Cloud Vertex AI Imagen
- Async PostgreSQL database for storing prompts and results
- FastAPI backend with full API documentation
- Docker support for easy deployment

## API Documentation

Once running, visit http://localhost:8000/docs for the full API documentation.

## API Endpoints
- `POST /avatars/` — Generate avatar from prompt
- `GET /avatars/{avatar_id}` — Retrieve avatar image and metadata
- `POST /avatars/{avatar_id}/regenerate` — Regenerate avatar

## Database
See `db/avatar_repository.py` for schema and migration details.

## Moderation & Logging
All prompts and generations are logged and moderated for security.

## Future Extensions
- Animation generation
- WebSocket progress updates
- Multi-agent orchestration
- Async background tasks 