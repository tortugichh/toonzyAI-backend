import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Конфигурация Redis из переменных окружения
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Создание экземпляра Celery
celery_app = Celery(
    "toonzy_animation",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.generation_tasks",
        "tasks.assembly_tasks"
    ]
)

# Настройки Celery
celery_app.conf.update(
    # Результаты задач
    result_expires=3600,  # Результаты хранятся 1 час
    result_backend_transport_options={'master_name': 'mymaster'},
    
    # Сериализация
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Таймауты
    task_time_limit=30 * 60,  # 30 минут максимум на задачу
    task_soft_time_limit=25 * 60,  # 25 минут мягкий лимит
    
    # Retry политика
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Настройки воркеров
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Логирование
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # Маршрутизация задач
    task_routes={
        'tasks.generation_tasks.*': {'queue': 'generation'},
        'tasks.assembly_tasks.*': {'queue': 'assembly'},
    },
    
    # Мониторинг
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Автоматическое обнаружение задач
celery_app.autodiscover_tasks()


# Функция для получения экземпляра Celery (для импорта в других модулях)
def get_celery_app() -> Celery:
    """Возвращает настроенный экземпляр Celery."""
    return celery_app 