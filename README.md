# ToonzyAI Avatar Generation Backend

This service generates personalized cartoon avatars from text prompts using a LangChain agent and Hugging Face diffusion models.

## Features
- Accepts creative prompts and user IDs via API
- Uses LangChain agent to orchestrate prompt validation, image generation, and moderation
- Stores prompt, image, and metadata in a PostgreSQL database
- Serves images as streams or base64
- Moderation and logging for security and auditing

## Tech Stack
- FastAPI
- Pydantic v2
- LangChain + langchain-huggingface
- Hugging Face FLUX.1-dev model
- AsyncPG + SQLAlchemy 2.0 (async)

## Setup
1. Clone the repo and `cd backend`
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables in a `.env` file:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/toonzyai
   HUGGINGFACEHUB_API_TOKEN=your_huggingface_token
   ```
4. Run migrations to set up the database (see below)
5. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

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