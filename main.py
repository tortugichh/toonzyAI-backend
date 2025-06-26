import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from routers import avatar_routes, auth_routes
from middleware.logging import LoggingMiddleware


load_dotenv()



# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ToonzyAI API",
    description="API for generating cartoon avatars using Vertex AI Imagen with JWT Authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # FastAPI dev server
        "https://your-frontend-domain.com",  # Production frontend domain
        # Add your actual frontend domains here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With"
    ],
)

# Logging middleware
app.add_middleware(LoggingMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры
app.include_router(avatar_routes.router, prefix="/api/v1", tags=["avatars"])
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["authentication"])

@app.get("/")
async def root():
    return {"message": "Welcome to ToonzyAI API"}

@app.get("/health")
async def health():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/test")
async def test():
    logger.info("Test endpoint accessed")
    return {"test": "API is working properly"}

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