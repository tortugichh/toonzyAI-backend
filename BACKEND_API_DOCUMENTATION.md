# 🎯 ToonzyAI Backend API Documentation

## Полная документация бэкенда для фронтенд разработчиков

> **Версия API:** 1.0.0  
> **Base URL:** `http://localhost:8000/api/v1`  
> **Swagger UI:** `http://localhost:8000/docs`  
> **ReDoc:** `http://localhost:8000/redoc`

---

## 📋 Содержание

- [Архитектура системы](#архитектура-системы)
- [Аутентификация](#аутентификация)
- [Endpoints Overview](#endpoints-overview)
- [Auth API](#auth-api)
- [Avatar API](#avatar-api)
- [Animation API](#animation-api)
- [Схемы данных](#схемы-данных)
- [Error Handling](#error-handling)
- [Workflow примеры](#workflow-примеры)
- [Настройка и развертывание](#настройка-и-развертывание)

---

## 🏗️ Архитектура системы

### Технологический стек:
- **FastAPI** - основной веб-фреймворк
- **PostgreSQL** - основная база данных
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **Redis + Celery** - очереди задач и фоновые процессы
- **Google Cloud Platform** - AI и хранение файлов
  - Vertex AI (Imagen, Veo 2.0) - генерация изображений и видео
  - Cloud Storage - хранение медиафайлов
- **JWT** - аутентификация и авторизация
- **Alembic** - миграции базы данных

### Основные сущности:

1. **User** - пользователи системы
2. **Avatar** - сгенерированные аватары
3. **AnimationProject** - проекты анимации (контейнеры для сегментов)
4. **AnimationSegment** - отдельные видео-сегменты анимации

### Асинхронная архитектура:

```mermaid
graph TD
    A[FastAPI Server] --> B[PostgreSQL]
    A --> C[Redis]
    C --> D[Celery Workers]
    D --> E[Google Cloud AI]
    D --> F[Google Cloud Storage]
    A --> G[JWT Auth]
```

---

## 🔐 Аутентификация

### Система авторизации:
- **JWT токены** с access (15 мин) и refresh (7 дней) токенами
- **Bearer token** в заголовке Authorization
- **Автоматическое обновление** токенов через refresh endpoint

### Заголовки запросов:
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Пример получения токена:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

## 🔑 Auth API

### POST `/auth/register` - Регистрация пользователя

Создает нового пользователя в системе.

**Request Body:**
```json
{
  "username": "string (3-50 символов, только буквы, цифры и _)",
  "email": "valid@email.com",
  "password": "string (минимум 8 символов)"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**
- `400` - Пользователь с таким username или email уже существует
- `422` - Неверный формат данных

### POST `/auth/login` - Аутентификация

Аутентифицирует пользователя и возвращает JWT токены.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**
- `401` - Неверные username или password
- `403` - Аккаунт пользователя деактивирован

### POST `/auth/token` - OAuth2 совместимая аутентификация

OAuth2 совместимый endpoint для Swagger UI и других OAuth2 клиентов.

**Request Body (form-data):**
```
username: string
password: string
grant_type: password (optional)
```

**Response:** Аналогично `/auth/login`

### POST `/auth/refresh` - Обновление токена

Обновляет access токен используя refresh токен.

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

**Response (200):**
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**
- `401` - Невалидный или истекший refresh токен

### GET `/auth/me` - Профиль пользователя

Возвращает информацию о текущем аутентифицированном пользователе.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### PUT `/auth/me` - Обновление профиля

Обновляет профиль текущего пользователя.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "username": "string (optional)",
  "email": "string (optional)",
  "password": "string (optional)"
}
```

**Response (200):** Обновленный профиль пользователя

**Errors:**
- `400` - Username или email уже заняты

### POST `/auth/change-password` - Изменение пароля

Изменяет пароль текущего пользователя.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string (минимум 8 символов)"
}
```

**Response (200):**
```json
{
  "message": "Password changed successfully"
}
```

**Errors:**
- `400` - Неверный текущий пароль

### POST `/auth/logout` - Выход

Выход из системы (в текущей реализации - информационный endpoint).

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

### GET `/auth/verify-token` - Проверка токена

Проверяет валидность текущего токена.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "valid": true,
  "user_id": "uuid",
  "username": "string",
  "expires_at": "2024-01-01T00:15:00Z"
}
```

---

## 📊 Endpoints Overview

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Регистрация нового пользователя |
| POST | `/auth/login` | Аутентификация пользователя |
| POST | `/auth/token` | OAuth2 совместимая аутентификация |
| POST | `/auth/refresh` | Обновление access токена |
| GET | `/auth/me` | Получение информации о текущем пользователе |
| PUT | `/auth/me` | Обновление профиля пользователя |
| POST | `/auth/change-password` | Изменение пароля |
| POST | `/auth/logout` | Выход из системы |
| GET | `/auth/verify-token` | Проверка валидности токена |

### Avatar Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/avatars/` | Создание нового аватара |
| GET | `/avatars/` | Получение списка аватаров пользователя |
| GET | `/avatars/{id}` | Получение информации об аватаре |
| GET | `/avatars/{id}/image` | Получение изображения аватара |
| DELETE | `/avatars/{id}` | Удаление аватара |

### Animation Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/animations/` | Создание проекта анимации |
| GET | `/animations/` | Список проектов анимации |
| GET | `/animations/{project_id}` | Получение проекта с сегментами |
| DELETE | `/animations/{project_id}` | Удаление проекта |
| POST | `/animations/{project_id}/assemble` | Сборка финального видео |
| GET | `/animations/{project_id}/video` | Получение финального видео |
| PUT | `/animations/{project_id}/segments/{segment_number}/prompt` | Обновление промпта сегмента |
| POST | `/animations/{project_id}/segments/{segment_number}/generate` | Генерация конкретного сегмента |
| GET | `/animations/{project_id}/segments/{segment_number}` | Детали сегмента |
| GET | `/animations/{project_id}/segments/{segment_number}/video` | Видео сегмента |

### Utility Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Проверка состояния сервера |

---

## 🎨 Avatar API

### POST `/avatars/` - Создание аватара

Создает новый аватар используя AI генерацию изображений.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "prompt": "string (описание желаемого аватара)"
}
```

**Response (200):**
```json
{
  "avatar_id": "uuid",
  "image_url": "/api/v1/avatars/{avatar_id}/image",
  "prompt": "string",
  "status": "completed",
  "user_id": "uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Описание процесса:**
1. Система получает промпт и запускает AI генерацию
2. Изображение генерируется с помощью Google Vertex AI Imagen
3. Результат сохраняется в базе данных
4. Возвращается информация о созданном аватаре

**Errors:**
- `500` - Ошибка при генерации аватара
- `401` - Пользователь не аутентифицирован

### GET `/avatars/` - Список аватаров

Возвращает список всех аватаров текущего пользователя с пагинацией.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `page` - номер страницы (по умолчанию: 1)
- `per_page` - количество элементов на странице (по умолчанию: 10, максимум: 100)

**Response (200):**
```json
{
  "avatars": [
    {
      "avatar_id": "uuid",
      "image_url": "/api/v1/avatars/{avatar_id}/image",
      "prompt": "string",
      "status": "completed",
      "user_id": "uuid",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 10
}
```

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/api/v1/avatars/?page=1&per_page=20" \
  -H "Authorization: Bearer <access_token>"
```

### GET `/avatars/{avatar_id}` - Информация об аватаре

Возвращает подробную информацию о конкретном аватаре.

**Headers:** `Authorization: Bearer <access_token>`

**Path Parameters:**
- `avatar_id` - UUID аватара

**Response (200):**
```json
{
  "avatar_id": "uuid",
  "user_id": "uuid",
  "prompt": "string",
  "status": "completed",
  "image_url": "/api/v1/avatars/{avatar_id}/image",
  "created_at": "2024-01-01T00:00:00Z",
  "moderation_flags": ["flag1", "flag2"] // или null
}
```

**Errors:**
- `404` - Аватар не найден
- `403` - Аватар не принадлежит текущему пользователю
- `400` - Неверный формат UUID

### GET `/avatars/{avatar_id}/image` - Изображение аватара

Возвращает файл изображения аватара.

**Headers:** `Authorization: Bearer <access_token>`

**Path Parameters:**
- `avatar_id` - UUID аватара

**Response (200):**
- **Content-Type:** `image/png`
- **Cache-Control:** `public, max-age=3600`
- **Content-Disposition:** `inline; filename=avatar_{avatar_id}.png`

**Binary data:** PNG изображение

**Errors:**
- `404` - Аватар или изображение не найдено
- `403` - Доступ запрещен

**Пример использования в HTML:**
```html
<img src="http://localhost:8000/api/v1/avatars/{avatar_id}/image" 
     alt="Avatar" 
     style="width: 256px; height: 256px;" />
```

### DELETE `/avatars/{avatar_id}` - Удаление аватара

Удаляет аватар из системы.

**Headers:** `Authorization: Bearer <access_token>`

**Path Parameters:**
- `avatar_id` - UUID аватара

**Response (200):**
```json
{
  "message": "Avatar deleted successfully",
  "avatar_id": "uuid"
}
```

**Errors:**
- `404` - Аватар не найден или нет прав на удаление
- `400` - Неверный формат UUID
- `500` - Ошибка сервера при удалении

---

## 🎬 Animation API

### Концепция работы с анимациями

**ToonzyAI использует систему сегментированной анимации:**

1. **AnimationProject** - контейнер для анимации с общим промптом
2. **AnimationSegment** - отдельные видео-клипы по 5 секунд каждый
3. **Пользовательский контроль** - вы управляете каждым сегментом индивидуально
4. **Финальная сборка** - склейка всех сегментов в один видеофайл

### Статусы анимации:
- `pending` - ожидает обработки
- `in_progress` - генерируется 
- `completed` - готово
- `failed` - ошибка генерации
- `assembling` - идет сборка финального видео

---

### POST `/animations/` - Создание проекта анимации

Создает новый проект анимации и запускает создание пустых сегментов.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "source_avatar_id": "uuid (ID аватара из /avatars/)",
  "total_segments": 5,
  "animation_prompt": "A cat in various dynamic poses performing different actions"
}
```

**Response (202):**
```json
{
  "id": "project_uuid",
  "user_id": "user_uuid",
  "source_avatar_id": "avatar_uuid",
  "total_segments": 5,
  "animation_prompt": "A cat in various dynamic poses performing different actions",
  "status": "pending",
  "final_video_url": null,
  "video_url": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "segments": []
}
```

**Важные моменты:**
- ✅ Система создает пустые сегменты асинхронно (~30-60 секунд)
- ✅ Каждый сегмент будет иметь статус `pending`
- ✅ Используйте polling для отслеживания создания сегментов
- ✅ Проект остается в статусе `pending` до генерации всех сегментов

**Errors:**
- `404` - Аватар не найден или не принадлежит пользователю
- `500` - Ошибка создания проекта

---

### GET `/animations/{project_id}` - Получение проекта

Возвращает проект анимации со всеми его сегментами.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "id": "project_uuid",
  "user_id": "user_uuid",
  "source_avatar_id": "avatar_uuid",
  "total_segments": 5,
  "animation_prompt": "A cat in various dynamic poses",
  "status": "pending",
  "final_video_url": "gs://bucket/final_video.mp4",
  "video_url": "/api/v1/animations/{project_id}/video",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "segments": [
    {
      "id": "segment_uuid",
      "segment_number": 1,
      "status": "pending",
      "segment_prompt": null,
      "start_frame_url": "gs://bucket/avatar_frame.jpg",
      "generated_video_url": null,
      "video_url": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Использование для polling:**
```javascript
const checkProjectStatus = async (projectId) => {
  const response = await fetch(`/api/v1/animations/${projectId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const project = await response.json();
  
  if (project.segments.length === 0) {
    console.log('Сегменты еще создаются...');
    setTimeout(() => checkProjectStatus(projectId), 5000);
  } else {
    console.log('Сегменты готовы:', project.segments.length);
  }
};
```

---

### GET `/animations/` - Список проектов

Возвращает список всех проектов анимации пользователя.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
[
  {
    "id": "project_uuid",
    "source_avatar_id": "avatar_uuid",
    "animation_prompt": "A cat in various dynamic poses",
    "status": "completed",
    "total_segments": 5,
    "final_video_url": "gs://bucket/final_video.mp4",
    "video_url": "/api/v1/animations/{project_id}/video",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### PUT `/animations/{project_id}/segments/{segment_number}/prompt` - Обновление промпта сегмента

Устанавливает или изменяет промпт для конкретного сегмента.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "segment_prompt": "A cat gracefully jumping over a wooden fence in slow motion"
}
```

**Response (200):**
```json
{
  "message": "Segment prompt updated successfully",
  "project_id": "project_uuid",
  "segment_number": 1,
  "new_prompt": "A cat gracefully jumping over a wooden fence in slow motion"
}
```

**Важно:**
- ✅ Промпт должен быть от 10 до 500 символов
- ✅ Можно обновлять промпт до и после генерации
- ✅ Перегенерация после изменения промпта возможна

---

### POST `/animations/{project_id}/segments/{segment_number}/generate` - Генерация сегмента

Запускает генерацию видео для конкретного сегмента.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "segment_prompt": "Опциональный промпт для генерации (переопределяет текущий)"
}
```

**Response (200):**
```json
{
  "message": "Segment generation started successfully! 🚀",
  "project_id": "project_uuid",
  "segment_number": 1,
  "task_id": "celery_task_uuid",
  "status": "in_progress",
  "prompt_used": "A cat gracefully jumping over a wooden fence",
  "estimated_time": "3-5 minutes",
  "current_time": "2024-01-01T00:00:00Z",
  "monitoring": {
    "status_endpoint": "/api/v1/animations/{project_id}/segments/{segment_number}",
    "video_endpoint": "/api/v1/animations/{project_id}/segments/{segment_number}/video",
    "poll_interval_seconds": 10
  },
  "details": {
    "generator": "Google Veo 2.0",
    "duration": "5 seconds",
    "quality": "1280x720",
    "user_control": true
  }
}
```

**Процесс генерации:**
1. Celery task запускается в фоне
2. Google Veo 2.0 генерирует видео (3-5 минут)
3. Результат сохраняется в Google Cloud Storage
4. Статус сегмента обновляется на `completed`

---

### GET `/animations/{project_id}/segments/{segment_number}` - Детали сегмента

Возвращает расширенную информацию о конкретном сегменте.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "id": "segment_uuid",
  "segment_number": 1,
  "status": "completed",
  "status_description": "✅ Video generated successfully",
  "prompts": {
    "active_prompt": "A cat gracefully jumping over a wooden fence",
    "prompt_source": "custom",
    "segment_prompt": "A cat gracefully jumping over a wooden fence",
    "project_prompt": "A cat in various dynamic poses"
  },
  "generation": {
    "generator": "Google Veo 2.0",
    "duration": "5 seconds",
    "quality": "1280x720",
    "estimated_time": "3-5 minutes"
  },
  "urls": {
    "start_frame_url": "gs://bucket/avatar.jpg",
    "generated_video_url": "gs://bucket/segment_video.mp4",
    "video_endpoint": "/api/v1/animations/project-uuid/segments/1/video",
    "download_endpoint": "/api/v1/animations/project-uuid/segments/1/video"
  },
  "actions": {
    "can_regenerate": true,
    "can_update_prompt": true,
    "generate_endpoint": "/api/v1/animations/project-uuid/segments/1/generate",
    "prompt_endpoint": "/api/v1/animations/project-uuid/segments/1/prompt"
  },
  "timestamps": {
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:15:30Z"
  },
  "user_control": {
    "enabled": true,
    "description": "You control when this segment generates"
  }
}
```

---

### GET `/animations/{project_id}/segments/{segment_number}/video` - Видео сегмента

Возвращает видеофайл сегмента с поддержкой Range requests для плавного воспроизведения.

**Headers:** `Authorization: Bearer <access_token>`

**Optional Headers:**
- `Range: bytes=0-1023` - для частичной загрузки

**Response (200/206):**
- **Content-Type:** `video/mp4`
- **Accept-Ranges:** `bytes`
- **Content-Length:** размер файла
- **Content-Range:** `bytes 0-1023/total_size` (для Range requests)

**Binary data:** MP4 видеофайл

**Пример использования в HTML:**
```html
<video controls width="640" height="360">
  <source src="/api/v1/animations/{project_id}/segments/{segment_number}/video" 
          type="video/mp4">
  Ваш браузер не поддерживает HTML5 видео.
</video>
```

---

### POST `/animations/{project_id}/assemble` - Сборка финального видео

Запускает сборку всех завершенных сегментов в одно финальное видео.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "message": "Video assembly started successfully",
  "project_id": "project_uuid",
  "status": "assembling"
}
```

**Условия для сборки:**
- ✅ Минимум 1 сегмент со статусом `completed`
- ✅ Автоматическая сборка происходит в фоне
- ✅ Результат доступен через `/animations/{project_id}/video`

---

### GET `/animations/{project_id}/video` - Финальное видео

Возвращает собранное финальное видео проекта.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
- **Content-Type:** `video/mp4`
- **Accept-Ranges:** `bytes`
- **Cache-Control:** `public, max-age=3600`

**Binary data:** MP4 видеофайл

**Errors:**
- `404` - Финальное видео еще не готово

---

### DELETE `/animations/{project_id}` - Удаление проекта

Удаляет проект анимации и все связанные сегменты.

**Headers:** `Authorization: Bearer <access_token>`

**Response (204):** No Content

**Важно:**
- ✅ Удаляются все сегменты проекта
- ✅ Удаляются файлы из Google Cloud Storage
- ✅ Операция необратима

---

## 📊 Схемы данных

### User Schema
```typescript
interface User {
  id: string;                    // UUID
  username: string;              // 3-50 символов, буквы, цифры, _
  email: string;                 // Валидный email
  is_active: boolean;            // Активен ли аккаунт
  is_verified: boolean;          // Подтвержден ли email
  created_at: string;            // ISO datetime
  updated_at: string;            // ISO datetime
}
```

### Avatar Schema  
```typescript
interface Avatar {
  avatar_id: string;             // UUID
  image_url: string;             // API endpoint для изображения
  prompt: string;                // Промпт для генерации
  status: "completed";           // Статус аватара
  user_id: string;               // UUID владельца
  created_at: string;            // ISO datetime
}

interface AvatarListResponse {
  avatars: Avatar[];
  total: number;                 // Общее количество
  page: number;                  // Текущая страница
  per_page: number;              // Элементов на странице
}
```

### Animation Project Schema
```typescript
interface AnimationProject {
  id: string;                    // UUID проекта
  user_id: string;               // UUID владельца
  source_avatar_id: string;      // UUID исходного аватара
  total_segments: number;        // Количество сегментов (1-10)
  animation_prompt: string;      // Общий промпт проекта
  status: AnimationStatus;       // Статус проекта
  final_video_url: string | null; // GCS URL финального видео
  video_url: string | null;      // API endpoint для видео
  created_at: string;            // ISO datetime
  updated_at: string;            // ISO datetime
  segments: AnimationSegment[];  // Массив сегментов
}
```

### Animation Segment Schema
```typescript
interface AnimationSegment {
  id: string;                    // UUID сегмента
  segment_number: number;        // Номер сегмента (1-N)
  status: AnimationStatus;       // Статус сегмента
  segment_prompt: string | null; // Индивидуальный промпт
  start_frame_url: string;       // GCS URL стартового кадра
  generated_video_url: string | null; // GCS URL видео
  video_url: string | null;      // API endpoint для видео
  created_at: string;            // ISO datetime
  updated_at: string;            // ISO datetime
}

type AnimationStatus = 
  | "pending"         // Ожидает обработки
  | "in_progress"     // Генерируется
  | "completed"       // Готово
  | "failed"          // Ошибка
  | "assembling";     // Идет сборка (только для проектов)
```

### Token Schema
```typescript
interface Token {
  access_token: string;          // JWT токен для запросов
  refresh_token: string;         // JWT токен для обновления
  token_type: "bearer";          // Тип токена
  expires_in: number;            // Время жизни в секундах (900)
}
```

---

## ⚠️ Error Handling

### Стандартные HTTP статусы

| Код | Значение | Описание |
|-----|----------|----------|
| 200 | OK | Успешный запрос |
| 201 | Created | Ресурс создан |
| 202 | Accepted | Запрос принят, обрабатывается асинхронно |
| 204 | No Content | Успешное удаление |
| 400 | Bad Request | Неверные параметры запроса |
| 401 | Unauthorized | Требуется аутентификация |
| 403 | Forbidden | Доступ запрещен |
| 404 | Not Found | Ресурс не найден |
| 422 | Unprocessable Entity | Ошибка валидации данных |
| 429 | Too Many Requests | Превышен лимит запросов |
| 500 | Internal Server Error | Ошибка сервера |

### Структура ошибок

```typescript
interface ErrorResponse {
  detail: string;                // Описание ошибки
  error_code?: string;           // Код ошибки (опционально)
  field_errors?: FieldError[];   // Ошибки валидации (опционально)
}

interface FieldError {
  field: string;                 // Название поля
  message: string;               // Сообщение об ошибке
}
```

### Примеры ошибок

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials",
  "error_code": "INVALID_TOKEN"
}
```

**422 Validation Error:**
```json
{
  "detail": "Validation error",
  "field_errors": [
    {
      "field": "username",
      "message": "Username must be between 3 and 50 characters"
    },
    {
      "field": "email", 
      "message": "Invalid email format"
    }
  ]
}
```

**404 Not Found:**
```json
{
  "detail": "Avatar not found or doesn't belong to current user"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error"
}
```

### Обработка ошибок в клиенте

```javascript
const handleApiError = (error) => {
  switch (error.status) {
    case 401:
      // Токен истек или недействителен
      redirectToLogin();
      break;
    case 403:
      // Недостаточно прав
      showErrorMessage("У вас нет прав для выполнения этой операции");
      break;
    case 404:
      // Ресурс не найден
      showErrorMessage("Запрашиваемый ресурс не найден");
      break;
    case 422:
      // Ошибки валидации
      showValidationErrors(error.field_errors);
      break;
    case 429:
      // Лимит запросов
      showErrorMessage("Слишком много запросов. Попробуйте позже.");
      break;
    case 500:
      // Ошибка сервера
      showErrorMessage("Ошибка сервера. Попробуйте позже.");
      break;
    default:
      showErrorMessage("Произошла неожиданная ошибка");
  }
};
```

---

## 🔄 Workflow примеры

### 1. Полный workflow создания анимации

```javascript
// 1. Создаем аватар
const createAvatar = async (prompt) => {
  const response = await fetch('/api/v1/avatars/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ prompt })
  });
  return response.json();
};

// 2. Создаем проект анимации
const createAnimationProject = async (avatarId, totalSegments, prompt) => {
  const response = await fetch('/api/v1/animations/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      source_avatar_id: avatarId,
      total_segments: totalSegments,
      animation_prompt: prompt
    })
  });
  return response.json();
};

// 3. Ждем создания сегментов
const waitForSegments = async (projectId) => {
  let attempts = 0;
  const maxAttempts = 24; // 2 минуты с интервалом 5 секунд
  
  while (attempts < maxAttempts) {
    const response = await fetch(`/api/v1/animations/${projectId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const project = await response.json();
    
    if (project.segments.length > 0) {
      console.log(`Создано ${project.segments.length} сегментов`);
      return project;
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
    attempts++;
  }
  
  throw new Error('Таймаут создания сегментов');
};

// 4. Настраиваем промпты для сегментов
const updateSegmentPrompt = async (projectId, segmentNumber, prompt) => {
  const response = await fetch(
    `/api/v1/animations/${projectId}/segments/${segmentNumber}/prompt`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ segment_prompt: prompt })
    }
  );
  return response.json();
};

// 5. Генерируем сегмент
const generateSegment = async (projectId, segmentNumber) => {
  const response = await fetch(
    `/api/v1/animations/${projectId}/segments/${segmentNumber}/generate`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    }
  );
  return response.json();
};

// 6. Мониторим генерацию сегмента
const waitForSegmentGeneration = async (projectId, segmentNumber) => {
  const pollInterval = 10000; // 10 секунд
  let attempts = 0;
  const maxAttempts = 30; // 5 минут
  
  while (attempts < maxAttempts) {
    const response = await fetch(
      `/api/v1/animations/${projectId}/segments/${segmentNumber}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const segment = await response.json();
    
    console.log(`Сегмент ${segmentNumber}: ${segment.status}`);
    
    if (segment.status === 'completed') {
      return segment;
    } else if (segment.status === 'failed') {
      throw new Error(`Генерация сегмента ${segmentNumber} не удалась`);
    }
    
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    attempts++;
  }
  
  throw new Error('Таймаут генерации сегмента');
};

// 7. Запускаем сборку финального видео
const assembleVideo = async (projectId) => {
  const response = await fetch(`/api/v1/animations/${projectId}/assemble`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Полный пример использования
const createFullAnimation = async () => {
  try {
    // 1. Создаем аватар
    const avatar = await createAvatar("A cute cartoon cat character");
    console.log("Аватар создан:", avatar.avatar_id);
    
    // 2. Создаем проект анимации
    const project = await createAnimationProject(
      avatar.avatar_id,
      5,
      "A cat performing various activities"
    );
    console.log("Проект создан:", project.id);
    
    // 3. Ждем создания сегментов
    const projectWithSegments = await waitForSegments(project.id);
    console.log("Сегменты готовы:", projectWithSegments.segments.length);
    
    // 4. Настраиваем промпты
    const prompts = [
      "A cat sitting peacefully in a sunny garden",
      "A cat playfully chasing a butterfly",
      "A cat jumping over a small fence",
      "A cat drinking water from a bowl",
      "A cat stretching and yawning"
    ];
    
    for (let i = 0; i < prompts.length; i++) {
      await updateSegmentPrompt(project.id, i + 1, prompts[i]);
    }
    
    // 5. Генерируем все сегменты
    for (let i = 1; i <= prompts.length; i++) {
      console.log(`Запускаем генерацию сегмента ${i}`);
      await generateSegment(project.id, i);
      await waitForSegmentGeneration(project.id, i);
      console.log(`Сегмент ${i} готов`);
    }
    
    // 6. Собираем финальное видео
    await assembleVideo(project.id);
    console.log("Финальное видео собирается...");
    
    // 7. Готово!
    console.log("Анимация готова! ID проекта:", project.id);
    
  } catch (error) {
    console.error("Ошибка создания анимации:", error);
  }
};
```

### 2. Polling статуса проекта

```javascript
const createProjectStatusChecker = (projectId, onUpdate) => {
  let polling = false;
  
  const poll = async () => {
    if (!polling) return;
    
    try {
      const response = await fetch(`/api/v1/animations/${projectId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const project = await response.json();
      
      onUpdate(project);
      
      // Продолжаем polling если есть активные процессы
      const hasActiveSegments = project.segments.some(segment => 
        segment.status === 'in_progress' || segment.status === 'pending'
      );
      
      if (hasActiveSegments || project.status === 'assembling') {
        setTimeout(poll, 5000); // 5 секунд
      } else {
        polling = false;
      }
      
    } catch (error) {
      console.error('Ошибка polling:', error);
      setTimeout(poll, 10000); // Retry через 10 секунд
    }
  };
  
  return {
    start: () => {
      polling = true;
      poll();
    },
    stop: () => {
      polling = false;
    }
  };
};

// Использование
const statusChecker = createProjectStatusChecker(projectId, (project) => {
  console.log('Статус проекта:', project.status);
  console.log('Готовых сегментов:', project.segments.filter(s => s.status === 'completed').length);
  
  // Обновляем UI
  updateProjectUI(project);
});

statusChecker.start();
```

### 3. Обработка токенов и автообновление

```javascript
class AuthManager {
  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
    this.isRefreshing = false;
    this.failedQueue = [];
  }
  
  async makeAuthenticatedRequest(url, options = {}) {
    const config = {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    };
    
    let response = await fetch(url, config);
    
    // Если токен истек, пытаемся обновить
    if (response.status === 401 && !this.isRefreshing) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        // Повторяем запрос с новым токеном
        config.headers['Authorization'] = `Bearer ${this.accessToken}`;
        response = await fetch(url, config);
      }
    }
    
    return response;
  }
  
  async refreshAccessToken() {
    if (this.isRefreshing) {
      // Если уже идет обновление, ждем его завершения
      return new Promise((resolve) => {
        this.failedQueue.push(resolve);
      });
    }
    
    this.isRefreshing = true;
    
    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken })
      });
      
      if (response.ok) {
        const tokens = await response.json();
        this.accessToken = tokens.access_token;
        this.refreshToken = tokens.refresh_token;
        
        localStorage.setItem('access_token', this.accessToken);
        localStorage.setItem('refresh_token', this.refreshToken);
        
        // Уведомляем ожидающие запросы
        this.failedQueue.forEach(resolve => resolve(true));
        this.failedQueue = [];
        
        return true;
      } else {
        // Refresh токен тоже истек
        this.logout();
        return false;
      }
    } catch (error) {
      console.error('Ошибка обновления токена:', error);
      this.logout();
      return false;
    } finally {
      this.isRefreshing = false;
    }
  }
  
  logout() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  }
}

// Использование
const auth = new AuthManager();

// Все API запросы через этот метод
const apiRequest = (url, options) => auth.makeAuthenticatedRequest(url, options);
```

---

## ⚙️ Настройка и развертывание

### Переменные окружения

Создайте `.env` файл в корне проекта:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/toonzyai

# JWT Authentication
SECRET_KEY=your-super-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Cloud
GOOGLE_CLOUD_PROJECT=extended-bongo-463404-r3
GCS_BUCKET=toonzyai
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key/service-account-key.json

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API Settings
API_V1_PREFIX=/api/v1
DEBUG=false
```

### Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### Настройка базы данных

```bash
# Создание миграций
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

### Запуск в development режиме

```bash
# Терминал 1: Запуск FastAPI сервера
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Терминал 2: Запуск Redis (если не установлен как сервис)
redis-server

# Терминал 3: Запуск Celery worker
celery -A utils.celery_app worker --loglevel=info --queues=generation,assembly,celery
```

### Запуск в production

```bash
# Gunicorn с несколькими воркерами
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Systemd сервис для Celery
sudo systemctl start celery
sudo systemctl enable celery
```

### Docker развертывание

```dockerfile
# Dockerfile уже готов в проекте
docker-compose up -d
```

---

## 🎯 Быстрый старт для фронтенда

### 1. Минимальный пример аутентификации

```javascript
const API_BASE = 'http://localhost:8000/api/v1';

// Регистрация
const register = async (username, email, password) => {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password })
  });
  return response.json();
};

// Вход
const login = async (username, password) => {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const tokens = await response.json();
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  return tokens;
};
```

---

## 💡 Лучшие практики

1. **Всегда обрабатывайте ошибки**
2. **Используйте polling для отслеживания асинхронных операций**
3. **Кэшируйте токены и обновляйте их автоматически**
4. **Показывайте пользователю прогресс генерации**
5. **Реализуйте retry механизмы для сетевых запросов**
6. **Используйте debouncing для пользовательских действий**
7. **Оптимизируйте загрузку медиафайлов с помощью lazy loading**

---

**🚀 Готово!** Теперь у вас есть полная документация для работы с ToonzyAI Backend API. Удачной разработки!

--- 