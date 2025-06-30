# 🎬 Настройка видео-генерации ToonzyAI

## ✅ Статус системы

Ваша система ToonzyAI настроена и готова к работе! 🎉

### Что работает:
- ✅ **Vertex AI подключение** - настроено и протестировано
- ✅ **Imagen для аватаров** - генерация изображений работает 
- ✅ **Celery для фоновых задач** - настроен
- ✅ **Mock видео-генерация** - работает как fallback
- ✅ **База данных анимаций** - структура готова
- ✅ **API endpoints** - `/animations/` доступны

### В процессе:
- 🔥 **Veo 3.0 Generate Preview** - код обновлен, ждем доступа от Google
- ✅ **Smart Fallback** - автоматически переключается на mock если Veo недоступен

## 🚀 Как запустить систему

### 1. Запуск основного сервера
```bash
cd /home/tortugich/Desktop/toonzyAI/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Запуск Celery worker (в отдельном терминале)
```bash
cd /home/tortugich/Desktop/toonzyAI/backend
source venv/bin/activate
celery -A utils.celery_app worker --loglevel=info
```

### 3. Запуск Redis (если не запущен)
```bash
sudo systemctl start redis-server
```

## 🎯 Тестирование

Запустите тест системы:
```bash
python test_real_animation.py
```

## 📋 API для создания анимации

### Создать анимационный проект
```bash
curl -X POST "http://localhost:8000/api/v1/animations/" \
-H "Content-Type: application/json" \
-d '{
  "source_avatar_id": "ваш_avatar_id",
  "total_segments": 3,
  "animation_prompt": "A cute robot dancing happily in a futuristic city"
}'
```

### Получить статус проекта
```bash
curl "http://localhost:8000/api/v1/animations/{project_id}"
```

## 🔧 Настройка Veo для реальной генерации видео

В настоящее время система использует mock-генерацию видео, так как:

1. **Veo требует специального доступа** - нужно запросить доступ к Veo Video API
2. **Региональная доступность** - Veo может быть недоступен в `us-central1`

### Как получить доступ к Veo:

1. **Свяжитесь с Google Cloud Support:**
   ```
   Запросите доступ к "Veo Video Generation API" для вашего проекта
   Project ID: extended-bongo-463404-r3
   ```

2. **Альтернативные регионы для Veo:**
   - `us-east5`
   - `europe-west1`
   - `asia-southeast1`

3. **Проверьте доступные модели:**
   ```bash
   gcloud ai models list --region=us-central1 --filter="displayName:veo"
   ```

## 🎬 Как работает система сейчас

1. **Пользователь создает анимацию** через API
2. **Система генерирует сегменты** в фоновом режиме через Celery
3. **Для каждого сегмента:**
   - Берется аватар из базы данных
   - Загружается в GCS 
   - Отправляется запрос к Veo (или mock)
   - Сохраняется результат
4. **Финальная сборка** всех сегментов в одно видео

## 🛠️ Переменные окружения (.env)

```env
# База данных
DATABASE_URL=postgresql+asyncpg://...

# Google Cloud
GOOGLE_CLOUD_PROJECT=extended-bongo-463404-r3
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key/key.json

# GCS
GCS_BUCKET_NAME=toonzyai

# Celery/Redis
REDIS_URL=redis://localhost:6379/0
```

## 📊 Мониторинг и логи

### Проверить статус Celery:
```bash
celery -A utils.celery_app inspect active
```

### Посмотреть логи приложения:
```bash
tail -f logs/toonzy.log
```

### Проверить статус Redis:
```bash
redis-cli ping
```

## 🔍 Отладка

### Если не работает генерация аватаров:
```bash
python -c "from utils.model_manager import test_vertex_ai_connection; print(test_vertex_ai_connection())"
```

### Если не работают Celery задачи:
```bash
python -c "from tasks.generation_tasks import test_celery; test_celery.delay()"
```

## 📝 Следующие шаги

1. **Получить доступ к Veo** от Google Cloud
2. **Настроить продакшн-окружение** с правильными доменами
3. **Добавить мониторинг** задач и ошибок
4. **Оптимизировать** производительность и затраты

---

🎉 **Поздравляем! Ваша система ToonzyAI настроена и готова к работе!** 