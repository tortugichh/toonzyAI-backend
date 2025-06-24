import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from utils.model_manager import warmup_pipeline
import threading
from routers.avatar_routes import router as avatar_router
from fastapi.staticfiles import StaticFiles

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Создаем приложение
app = FastAPI(
    title="ToonzyAI Avatar Generation API",
    description="API for generating AI avatars",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Базовые маршруты для тестирования
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "ToonzyAI Avatar Generation API is running", "status": "ok"}

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
    
    # Прогрев модели в отдельном потоке
    threading.Thread(target=warmup_pipeline, daemon=True).start()
    logger.info("Startup completed successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down ToonzyAI API...")

# Импортируем роутеры - убираем try-catch для отладки
logger.info("Loading avatar routes...")
app.include_router(avatar_router, prefix="/avatars", tags=["avatars"])
logger.info("Avatar routes loaded successfully")

logger.info("Loading storyboard routes...")
app.include_router(storyboard_router, prefix="/storyboards", tags=["storyboards"])
logger.info("Storyboard routes loaded successfully")

# Обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
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