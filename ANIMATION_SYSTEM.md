# 🎬 ToonzyAI Animation System

Система пошаговой видео-анимации для генерации видео из статичных изображений с использованием мультиагентной архитектуры.

## 🏗️ Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI API   │    │  Celery Workers │    │   Databases     │
│                 │    │                 │    │                 │
│ Authentication  │◄──►│ Generation      │◄──►│ PostgreSQL      │
│ Animation CRUD  │    │ Assembly        │    │ Redis (broker)  │
│ Status Tracking │    │ Error Handling  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Google Cloud  │    │      FFmpeg     │    │    Vertex AI    │
│                 │    │                 │    │                 │
│ Storage (GCS)   │    │ Video Assembly  │    │ Imagen Video    │
│ File Management │    │ Frame Extract   │    │ Generation      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Реализованные компоненты

### ✅ **1. Модели базы данных**
- **AnimationProject**: Управление проектами анимации
- **AnimationSegment**: Индивидуальные видео-сегменты
- **AnimationStatus**: Статусы выполнения (pending, in_progress, completed, failed, assembling)

### ✅ **2. API Endpoints**
```
POST   /api/v1/animations/                    # Создание проекта
GET    /api/v1/animations/{project_id}        # Статус проекта
GET    /api/v1/animations/                    # Список проектов
POST   /api/v1/animations/{project_id}/assemble  # Сборка видео
DELETE /api/v1/animations/{project_id}        # Удаление проекта
```

### ✅ **3. Мультиагентная система (Celery)**

#### **Agent 1: Generation Tasks**
- `create_animation_segments_task`: Создание записей сегментов
- `generate_segment_task`: Генерация отдельных видео-сегментов
- Автоматическая цепочка: сегмент 1 → сегмент 2 → ... → сегмент N

#### **Agent 2: Assembly Tasks**
- `assemble_video_task`: Сборка финального видео
- `check_segments_completion_task`: Проверка готовности сегментов
- FFmpeg-based concatenation

### ✅ **4. Интеграции**
- **Vertex AI**: Генерация видео из изображений (Imagen Video)
- **Google Cloud Storage**: Хранение видеофайлов и кадров
- **FFmpeg**: Обработка видео, извлечение кадров, сборка
- **JWT Authentication**: Безопасность и изоляция пользователей

## 🔄 Workflow процесса анимации

```
1. Пользователь создает проект анимации
   ↓
2. Система создает записи сегментов в БД
   ↓
3. Agent 1 генерирует сегмент 1 из исходного изображения
   ↓
4. Agent 1 извлекает последний кадр из сегмента 1
   ↓
5. Agent 1 генерирует сегмент 2 из последнего кадра сегмента 1
   ↓
6. Повторяется для всех сегментов...
   ↓
7. Agent 2 проверяет готовность всех сегментов
   ↓
8. Agent 2 скачивает все сегменты из GCS
   ↓
9. Agent 2 собирает финальное видео через FFmpeg
   ↓
10. Финальное видео загружается в GCS
```

## 📋 Требования системы

### **Обязательные зависимости:**
```bash
# Python packages (уже установлены)
celery[redis]>=5.3.0
redis>=4.5.0
ffmpeg-python
google-cloud-aiplatform
google-cloud-storage

# Системные зависимости
sudo apt-get install ffmpeg redis-server
```

### **Переменные окружения:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/toonzy

# Redis (для Celery)
REDIS_URL=redis://localhost:6379/0

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
GCS_BUCKET=your-storage-bucket

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## 🚀 Запуск системы

### **1. Запуск FastAPI сервера:**
```bash
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **2. Запуск Redis сервера:**
```bash
sudo systemctl start redis-server
# или
redis-server
```

### **3. Запуск Celery Worker:**
```bash
source venv/bin/activate
celery -A celery_worker worker --loglevel=info
```

### **4. (Опционально) Мониторинг Celery:**
```bash
celery -A celery_worker flower
# Доступен на http://localhost:5555
```

## 🧪 Тестирование

### **Автоматический тест:**
```bash
python test_animation_system.py
```

### **Ручное тестирование через API:**
```bash
# 1. Регистрация
curl -X POST http://localhost:8000/api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"username":"testuser","email":"test@test.com","password":"password123"}'

# 2. Авторизация
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"testuser","password":"password123"}'

# 3. Создание анимации
curl -X POST http://localhost:8000/api/v1/animations/ \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{
    "source_avatar_id": "AVATAR_UUID",
    "total_segments": 3,
    "animation_prompt": "Character walking in a magical forest"
  }'

# 4. Проверка статуса
curl -X GET http://localhost:8000/api/v1/animations/PROJECT_UUID \\
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 Мониторинг и логирование

- **FastAPI логи**: Автоматические запросы и ошибки
- **Celery логи**: Статусы задач и обработка ошибок
- **Database логи**: SQL запросы и транзакции

## 🔧 Конфигурация производства

### **Celery Production Setup:**
```bash
# Supervisor или systemd для автозапуска
celery -A celery_worker worker --loglevel=info --concurrency=4

# Flower для мониторинга
celery -A celery_worker flower --port=5555
```

### **Redis Production:**
```bash
# Настройка персистентности
redis-server --appendonly yes

# Мониторинг памяти
redis-cli info memory
```

## 📈 Возможности масштабирования

1. **Горизонтальное масштабирование Celery**: Добавление воркеров
2. **Очереди по приоритетам**: Разделение генерации и сборки
3. **Мониторинг производительности**: Prometheus + Grafana
4. **Кэширование**: Промежуточные результаты в Redis
5. **CDN интеграция**: Для быстрой доставки видео

## 🛡️ Безопасность

- **JWT аутентификация**: Защита всех эндпоинтов
- **Изоляция пользователей**: Доступ только к своим проектам
- **Валидация входных данных**: Pydantic схемы
- **Ограничения ресурсов**: Лимиты на количество сегментов
- **Error handling**: Безопасная обработка ошибок без утечки данных

## 🎯 Статусы системы

- ✅ **FastAPI сервер**: Полностью реализован и протестирован
- ✅ **База данных**: Модели и миграции готовы
- ✅ **Authentication**: JWT система работает
- ✅ **API Endpoints**: Все эндпоинты реализованы
- ✅ **Celery Workers**: Мультиагентная система готова
- 🟡 **Vertex AI**: Mock реализация (требует настройки GCP)
- 🟡 **GCS Storage**: Требует настройки bucket и credentials
- 🟡 **Production Deployment**: Требует настройки инфраструктуры

## 📚 Дополнительные ресурсы

- **FastAPI Documentation**: http://localhost:8000/docs
- **Celery Monitoring**: http://localhost:5555 (если запущен Flower)
- **Database Migrations**: `alembic upgrade head`
- **Security Guide**: См. `SECURITY.md`

---

**🎉 Система готова к использованию!** 

Для полного функционирования необходимо настроить Google Cloud credentials и запустить все компоненты. 