import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from routers import avatar_routes, auth_routes, animation_routes, progress_ws, story_routes
from middleware.logging import LoggingMiddleware
from contextlib import asynccontextmanager

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS origins из переменной окружения
origins_env = os.getenv("CORS_ORIGINS", "")
extra_origins = [o.strip() for o in origins_env.split(',') if o.strip()]

# Добавляем все нужные фронтенд-URL
frontend_origins = [
    "https://toonzyai.me",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
]

# Объединяем с origins из переменной окружения (если есть)
allow_origins = list(set(frontend_origins + extra_origins))

app = FastAPI(
    title="ToonzyAI API",
    description="API for generating cartoon avatars using Vertex AI Imagen with JWT Authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware with security considerations
default_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
]

allow_origins = default_origins + extra_origins if extra_origins else default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ],
)

# Logging middleware
app.add_middleware(LoggingMiddleware)

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры
app.include_router(avatar_routes.router, prefix="/api/v1", tags=["avatars"])
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(animation_routes.router, prefix="/api/v1/animations", tags=["animations"])
app.include_router(progress_ws.router, prefix="/api/ws", tags=["websocket"])
app.include_router(story_routes.router, prefix="/api/v1", tags=["stories"])

@app.get("/health")
async def health():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy", "version": "1.0.0"}

# Test and demo endpoints removed

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up ToonzyAI API...")
    
    # Проверяем переменные окружения
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info("Database URL configured")
    else:
        logger.warning("DATABASE_URL not found in environment variables")
    
    logger.info("Startup completed successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down ToonzyAI API...")

# Обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        log_level="info"
    )