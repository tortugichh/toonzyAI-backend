# ToonzyAI Frontend Integration Guide (Full)

## 0. TL;DR
1. Запустите backend в Docker (`docker compose up -d backend celery db redis`).  
2. Фронт (Vite) проксирует `/api` → `http://localhost:8000`.  
3. Авторизация: `POST /api/v1/auth/register` → `POST /api/v1/auth/token` (JWT).  
4. Генерация: аватар → проект → сегменты; poll `…/status` для прогресса.  
5. Готовые URL-ы указывают на Google Cloud Storage; public bucket или signed URL.

---

## 1. Запуск окружения
```bash
# backend
cd backend
docker compose up -d db redis
alembic upgrade head   # миграции (avatars.progress, …)
docker compose up -d backend celery

# frontend
cd frontend/toonzyai-frontend
npm i
npm run dev  # http://localhost:5173
```
`vite.config.ts` (proxy):
```ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
```

---

## 2. Аутентификация
### 2.1 Регистрация
`POST /api/v1/auth/register`
```jsonc
{
  "username": "neo",
  "email": "neo@matrix.io",
  "password": "pa55word"
}
```

### 2.2 Получение токенов
`POST /api/v1/auth/token` (`grant_type=password`)
```form
username=neo@matrix.io&password=pa55word
```
Ответ:
```jsonc
{
  "access_token": "<JWT>",
  "refresh_token": "<JWT>"
}
```
Добавляйте в запросы:
```http
Authorization: Bearer <access_token>
```
*Важно:* `access_token` живёт 30 мин; при 401 — обновить через `/refresh`.

---

## 3. Аватары
| Действие | Метод | Путь |
|----------|-------|------|
| Создать   | POST | `/avatars/` |
| Статус    | GET  | `/avatars/{id}/status` |
| Файл      | GET  | `/avatars/{id}/image` |
| Список    | GET  | `/avatars/?page=1&per_page=10` |
| Удалить   | DELETE | `/avatars/{id}` |

### 3.1 Создание
```ts
await fetch('/api/v1/avatars/', {
  method: 'POST',
  headers: authHeader(),
  body: JSON.stringify({ prompt }),
});
```
Ответ содержит `avatar_id` & `status=pending`.

### 3.2 Polling
```ts
const { progress, status } = useProgress(`/api/v1/avatars/${id}/status`);
```
При `progress === 100 && status === 'completed'` → получить `image`.

---

## 4. Анимация
### 4.1 Создать проект
`POST /api/v1/animations/`
```jsonc
{
  "total_segments": 3,
  "animation_prompt": "epic cyberpunk city skyline",
  "source_avatar_id": "<avatar_uuid>"
}
```
Ответ: `project_id` + массив созданных сегментов.

### 4.2 Сегменты
| Действие | Метод | Путь |
|----------|-------|------|
| Создать сегмент | POST | `/animations/{project_id}/segments/` |
| Запустить генерацию | POST | `/animations/segments/{segment_id}/generate` |
| Статус  | GET | `/animations/segments/{segment_id}/status` |
| Получить подп.-URL | POST | `/animations/segments/{segment_id}/signed_url` |

*Frontend flow*
1. Пользователь редактирует текст-промпт сегмента.
2. `POST …/generate` — Celery ставится в очередь.
3. Poll `…/status` (progress). 10 → 30 → 90 → 100.
4. После 100% — `video_url` доступен ➜ `<video src>`.

---

## 5. Прогресс-бар API
`progress` — целое 0–100. Ступени:
* **avatars**: 10 (иниц) → 50 (изображение готово) → 80 (загружено) → 100.
* **segments**: 10 (IN_PROGRESS) → 30 (start_frame готов) → 90 (видео загружено) → 100.

Статусы:
* `pending`, `in_progress`, `completed`, `failed`.

### Ошибки
| HTTP | Причина |
|------|---------|
| 401  | access_token истёк / отсутствует |
| 403  | объект не принадлежит пользователю |
| 404  | not found (неверный id) |
| 500  | внутренняя ошибка (логировать) |

---

## 6. Примеры React-компонентов
### 6.1 ProgressBar.tsx
```tsx
function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full bg-gray-200 rounded">
      <div
        className="h-full bg-indigo-500 rounded"
        style={{ width: `${value}%`, transition: 'width 0.5s' }}
      />
    </div>
  );
}
```
### 6.2 Использование
```tsx
const status = useProgress(`/api/v1/avatars/${id}/status`);
return <ProgressBar value={status?.progress ?? 0} />;
```

---

## 7. Deployment notes
* Uniform bucket-level access включён, поэтому объекты читаются без ACL.  
* Если решите отключить Public — backend уже умеет возвращать signed URLs.
* Celery воркер обрабатывает очереди `generation`, `assembly`.
* Высоконагруженная очередь → масштабируйте контейнер `celery` и Redis.

---

## 8. Ссылки
* **Backend OpenAPI**: `http://localhost:8000/docs`
* **DB schema**: `db/avatar_repository.py`, Alembic migrations
* **Figma UI** (если есть)

---

Happy hacking! 🎨🎞️ 