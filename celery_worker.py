#!/usr/bin/env python3
"""
Celery Worker для ToonzyAI Animation System
Запуск: celery -A celery_worker worker --loglevel=info
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Импортируем Celery приложение
from utils.celery_app import celery_app

# Импортируем задачи для их регистрации
import tasks.generation_tasks
import tasks.assembly_tasks

if __name__ == '__main__':
    # Запуск воркера из командной строки
    celery_app.start() 