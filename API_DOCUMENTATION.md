# 📚 ToonzyAI API Documentation

Полная документация по всем эндпойнтам ToonzyAI Backend API для создания анимированных аватаров.

## 🔐 Аутентификация

Все защищенные эндпойнты требуют JWT токен в заголовке:
```
Authorization: Bearer <your_jwt_token>
```

---

## 🏥 Системные эндпойнты

### GET `/health`
Проверка работоспособности API.

**Ответ:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 🔑 Аутентификация (`/api/v1/auth`)

### POST `/api/v1/auth/register`
Регистрация нового пользователя.

**Тело запроса:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password123"
}
```

**Ответ (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### POST `/api/v1/auth/login`
Аутентификация пользователя.

**Тело запроса:**
```json
{
  "username": "john_doe",
  "password": "secure_password123"
}
```

**Ответ (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST `/api/v1/auth/token`
OAuth2 совместимый логин (для Swagger UI).

**Form Data:**
```
username: john_doe
password: secure_password123
```

**Ответ (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### POST `/api/v1/auth/refresh`
Обновление access токена.

**Тело запроса:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Ответ (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET `/api/v1/auth/me`
Получение профиля текущего пользователя.

🔒 **Требует авторизации**

**Ответ (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### PUT `/api/v1/auth/me`
Обновление профиля пользователя.

🔒 **Требует авторизации**

**Тело запроса:**
```json
{
  "username": "new_username",
  "email": "new_email@example.com"
}
```

**Ответ (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "new_username",
  "email": "new_email@example.com",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### POST `/api/v1/auth/change-password`
Смена пароля пользователя.

🔒 **Требует авторизации**

**Тело запроса:**
```json
{
  "current_password": "old_password123",
  "new_password": "new_secure_password456"
}
```

**Ответ (200):**
```json
{
  "message": "Password changed successfully"
}
```

### POST `/api/v1/auth/logout`
Выход из системы.

🔒 **Требует авторизации**

**Ответ (200):**
```json
{
  "message": "Successfully logged out"
}
```

### GET `/api/v1/auth/verify-token`
Проверка валидности токена.

🔒 **Требует авторизации**

**Ответ (200):**
```json
{
  "valid": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "expires_at": "2024-01-01T12:30:00Z"
}
```

---

## 👤 Аватары (`/api/v1`)

### POST `/api/v1/avatars/`
Создание нового аватара.

🔒 **Требует авторизации**

**Тело запроса:**
```json
{
  "prompt": "Beautiful cartoon character, anime style, smiling, colorful background"
}
```

**Ответ (201):**
```json
{
  "avatar_id": "660e8400-e29b-41d4-a716-446655440000",
  "image_url": "/api/v1/avatars/660e8400-e29b-41d4-a716-446655440000/image",
  "prompt": "Beautiful cartoon character, anime style, smiling, colorful background",
  "status": "completed",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### GET `/api/v1/avatars/`
Получение списка аватаров пользователя с пагинацией.

🔒 **Требует авторизации**

**Query параметры:**
- `page` (int, default=1): Номер страницы
- `per_page` (int, default=10, max=100): Количество элементов на странице

**Пример запроса:**
```
GET /api/v1/avatars/?page=1&per_page=5
```

**Ответ (200):**
```json
{
  "avatars": [
    {
      "avatar_id": "660e8400-e29b-41d4-a716-446655440000",
      "image_url": "/api/v1/avatars/660e8400-e29b-41d4-a716-446655440000/image",
      "prompt": "Beautiful cartoon character, anime style",
      "status": "completed",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 5
}
```

### GET `/api/v1/avatars/{avatar_id}`
Получение информации об аватаре.

🔒 **Требует авторизации** (только собственные аватары)

**Ответ (200):**
```json
{
  "avatar_id": "660e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt": "Beautiful cartoon character, anime style, smiling",
  "status": "completed",
  "image_url": "/api/v1/avatars/660e8400-e29b-41d4-a716-446655440000/image",
  "created_at": "2024-01-01T12:00:00Z",
  "moderation_flags": null
}
```

### GET `/api/v1/avatars/{avatar_id}/image`
Получение изображения аватара.

🔒 **Требует авторизации** (только собственные аватары)

**Ответ (200):**
- Content-Type: `image/png`
- Binary image data
- Headers:
  - `Content-Disposition: inline; filename=avatar_{avatar_id}.png`
  - `Cache-Control: public, max-age=3600`

### DELETE `/api/v1/avatars/{avatar_id}`
Удаление аватара.

🔒 **Требует авторизации** (только собственные аватары)

**Ответ (200):**
```json
{
  "message": "Avatar deleted successfully",
  "avatar_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

---

## 🎬 Анимационные проекты (`/api/v1/animations`)

### POST `/api/v1/animations/`
Создание нового анимационного проекта.

🔒 **Требует авторизации**

**Тело запроса:**
```json
{
  "source_avatar_id": "660e8400-e29b-41d4-a716-446655440000",
  "total_segments": 3,
  "animation_prompt": "Character walking happily in a magical forest"
}
```

**Ответ (202):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_avatar_id": "660e8400-e29b-41d4-a716-446655440000",
  "total_segments": 3,
  "animation_prompt": "Character walking happily in a magical forest",
  "status": "pending",
  "final_video_url": null,
  "video_url": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "segments": []
}
```

### GET `/api/v1/animations/{project_id}`
Получение статуса анимационного проекта и всех его сегментов.

🔒 **Требует авторизации** (только собственные проекты)

**Ответ (200):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_avatar_id": "660e8400-e29b-41d4-a716-446655440000",
  "total_segments": 3,
  "animation_prompt": "Character walking happily in a magical forest",
  "status": "in_progress",
  "final_video_url": null,
  "video_url": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:05:00Z",
  "segments": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "segment_number": 1,
      "status": "completed",
      "start_frame_url": "https://storage.googleapis.com/toonzyai/avatars/...",
      "generated_video_url": "https://storage.googleapis.com/toonzyai/animations/...",
      "video_url": "/api/v1/animations/770e8400-e29b-41d4-a716-446655440000/segments/1/video",
      "created_at": "2024-01-01T12:01:00Z",
      "updated_at": "2024-01-01T12:03:00Z"
    },
    {
      "id": "990e8400-e29b-41d4-a716-446655440000",
      "segment_number": 2,
      "status": "in_progress",
      "start_frame_url": "https://storage.googleapis.com/toonzyai/animations/...",
      "generated_video_url": null,
      "video_url": null,
      "created_at": "2024-01-01T12:03:00Z",
      "updated_at": "2024-01-01T12:04:00Z"
    }
  ]
}
```

**Возможные статусы проекта:**
- `pending` - Проект создан, ожидает обработки
- `in_progress` - Генерация сегментов в процессе
- `assembling` - Сборка финального видео
- `completed` - Проект завершен
- `failed` - Произошла ошибка

### GET `/api/v1/animations/`
Получение списка всех анимационных проектов пользователя.

🔒 **Требует авторизации**

**Ответ (200):**
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "source_avatar_id": "660e8400-e29b-41d4-a716-446655440000",
    "animation_prompt": "Character walking happily in a magical forest",
    "status": "completed",
    "total_segments": 3,
    "final_video_url": "https://storage.googleapis.com/toonzyai/animations/...",
    "video_url": "/api/v1/animations/770e8400-e29b-41d4-a716-446655440000/video",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### POST `/api/v1/animations/{project_id}/assemble`
Принудительный запуск сборки финального видео.

🔒 **Требует авторизации** (только собственные проекты)

**Ответ (200):**
```json
{
  "message": "Video assembly started",
  "project_id": "770e8400-e29b-41d4-a716-446655440000",
  "status": "assembling"
}
```

**Возможные ошибки:**
- `400` - Не все сегменты готовы / видео уже собрано / сборка уже идет
- `404` - Проект не найден

### DELETE `/api/v1/animations/{project_id}`
Удаление анимационного проекта и всех связанных сегментов.

🔒 **Требует авторизации** (только собственные проекты)

**Ответ (204):**
```
No Content
```

### GET `/api/v1/animations/{project_id}/video`
Получение финального видео анимации с поддержкой Range requests.

🔒 **Требует авторизации** (только собственные проекты)

**Headers (опционально):**
- `Range: bytes=0-1023` - Для загрузки части файла

**Ответ (200/206):**
- Content-Type: `video/mp4`
- Binary video data
- Headers:
  - `Accept-Ranges: bytes`
  - `Content-Length: {size}`
  - `Content-Disposition: inline; filename=animation_{project_id}.mp4`
  - `Cache-Control: public, max-age=3600`

### GET `/api/v1/animations/{project_id}/segments/{segment_number}/video`
Получение видео отдельного сегмента с поддержкой Range requests.

🔒 **Требует авторизации** (только собственные проекты)

**Headers (опционально):**
- `Range: bytes=0-1023` - Для загрузки части файла

**Ответ (200/206):**
- Content-Type: `video/mp4`
- Binary video data
- Headers:
  - `Accept-Ranges: bytes`
  - `Content-Length: {size}`
  - `Content-Disposition: inline; filename=segment_{segment_number}_{project_id}.mp4`
  - `Cache-Control: public, max-age=3600`

### HEAD `/api/v1/animations/{project_id}/video`
Получение метаданных финального видео без загрузки контента.

🔒 **Требует авторизации** (только собственные проекты)

**Ответ (200):**
- Headers:
  - `Accept-Ranges: bytes`
  - `Content-Length: {size}`
  - `Content-Type: video/mp4`
  - `Cache-Control: public, max-age=3600`
  - `X-Video-Duration: unknown`
  - `X-Video-Status: ready`

---

## 🔥 Коды ошибок

### Общие коды
- `200` - Успешный запрос
- `201` - Ресурс создан
- `202` - Запрос принят в обработку
- `204` - Успешно, без контента
- `206` - Частичный контент (Range request)

### Ошибки клиента (4xx)
- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Ресурс не найден
- `422` - Ошибка валидации данных

### Ошибки сервера (5xx)
- `500` - Внутренняя ошибка сервера
- `503` - Сервис недоступен

**Формат ошибки:**
```json
{
  "detail": "Описание ошибки"
}
```

---

## 🔄 Типичные сценарии использования

### 1. Регистрация и создание аватара
```bash
# 1. Регистрация
POST /api/v1/auth/register
{
  "username": "user123",
  "email": "user@example.com", 
  "password": "password123"
}

# 2. Логин
POST /api/v1/auth/login
{
  "username": "user123",
  "password": "password123"
}
# Получаем access_token

# 3. Создание аватара
POST /api/v1/avatars/
Authorization: Bearer {access_token}
{
  "prompt": "Cute anime character with blue hair"
}
# Получаем avatar_id
```

### 2. Создание анимации
```bash
# 1. Создание проекта анимации
POST /api/v1/animations/
Authorization: Bearer {access_token}
{
  "source_avatar_id": "{avatar_id}",
  "total_segments": 2,
  "animation_prompt": "Character dancing happily"
}
# Получаем project_id

# 2. Проверка статуса
GET /api/v1/animations/{project_id}
Authorization: Bearer {access_token}

# 3. Когда готово - скачивание видео
GET /api/v1/animations/{project_id}/video
Authorization: Bearer {access_token}
```

### 3. Работа с Range requests для больших файлов
```bash
# 1. Получение размера файла
HEAD /api/v1/animations/{project_id}/video
Authorization: Bearer {access_token}
# Читаем Content-Length из headers

# 2. Загрузка частями
GET /api/v1/animations/{project_id}/video
Authorization: Bearer {access_token}
Range: bytes=0-1048575
# Получаем первый мегабайт (0-1MB)

GET /api/v1/animations/{project_id}/video  
Authorization: Bearer {access_token}
Range: bytes=1048576-2097151
# Получаем второй мегабайт (1-2MB)
```

---

## 🚀 Swagger UI

Интерактивная документация доступна по адресу:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🛡️ Безопасность

- Все чувствительные эндпойнты защищены JWT аутентификацией
- Пользователи имеют доступ только к своим ресурсам
- Поддержка CORS для фронтенд интеграции
- Валидация всех входящих данных через Pydantic
- Логирование всех запросов через middleware

---

## 📊 Лимиты

- **Аватары на пользователя**: Без ограничений
- **Анимационные проекты**: Без ограничений  
- **Сегменты в проекте**: 1-10
- **Размер файлов**: До 100MB для видео
- **Пагинация**: Максимум 100 элементов на страницу
- **JWT токен**: Действует 30 минут
- **Refresh токен**: Действует 7 дней

---

## 🔧 Технические детали

- **Фреймворк**: FastAPI
- **База данных**: PostgreSQL с SQLAlchemy
- **Аутентификация**: JWT с refresh токенами
- **Файловое хранилище**: Google Cloud Storage
- **Очередь задач**: Celery с Redis
- **AI модели**: Vertex AI Imagen (аватары), Veo 2.0/RunwayML (видео)
- **Обработка видео**: FFmpeg 