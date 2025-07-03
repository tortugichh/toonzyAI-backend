# ToonzyAI • Frontend ⇄ Backend Progress API Guide

## Базовые URL-ы

| Environment | Backend URL | Vite proxy |
|-------------|-------------|------------|
| Docker (local) | `http://localhost:8000` | `'/api' → 'http://localhost:8000'` |
| Production | `https://api.toonzyai.com` | настройте в `.env` фронта |

Все дальнейшие пути начинаются с `/api/v1`.

> Фронт отправляет заголовок `Authorization: Bearer <JWT>` для всех защищённых запросов.

---

## 1. Аватары

### 1.1 Создание аватара
`POST /avatars/`
```jsonc
{
  "prompt": "cartoon character with blue hair holding a surfboard"
}
```
Ответ `200`:
```jsonc
{
  "avatar_id": "69718cfa-…",
  "image_url": "/api/v1/avatars/69718cfa-…/image",
  "prompt": "cartoon character with blue hair holding a surfboard",
  "status": "pending",
  "user_id": "e52b…",
  "created_at": "2025-07-02T10:00:01Z"
}
```

### 1.2 Проверка прогресса
`GET /avatars/{avatar_id}/status`
```jsonc
{
  "avatar_id": "69718cfa-…",
  "status": "in_progress",   // pending / in_progress / completed / failed
  "progress": 50              // 0–100 %
}
```
Polling рекоммендуется раз в ~2 с. Когда `progress == 100` и `status == completed`, картинку можно получить по `image_url` (`GET /avatars/{id}/image`).

---

## 2. Анимационные проекты и сегменты

### 2.1 Создать сегмент
`POST /animations/{project_id}/segments/`
```jsonc
{
  "segment_number": 2,
  "segment_prompt": "hero jumps into the sea"
}
```
Ответ `202`, в теле — `segment_id`.

### 2.2 Запустить генерацию
`POST /animations/segments/{segment_id}/generate`

### 2.3 Отслеживать прогресс сегмента
`GET /animations/segments/{segment_id}/status`
```jsonc
{
  "segment_id": "3a90…",
  "status": "in_progress",   // pending / in_progress / completed / failed
  "progress": 70,
  "video_url": null            // появится при 100 %
}
```
Когда `progress == 100` → `video_url` содержит mp4 в GCS и доступен по HTTPS.

---

## 3. Сводка статусов

| Entity  | Status flow                               |
|---------|-------------------------------------------|
| Avatar  | pending → in_progress → completed/failed |
| Segment | pending → in_progress → completed/failed |
| progress| 0 → 100 % (обновляется сервером)         |

---

## 4. Рекоммендации по фронту

### React-hook для polling
```ts
function useProgress(url: string, interval = 2000) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    async function tick() {
      const res = await fetch(url, { headers: authHeader() });
      const json = await res.json();
      setData(json);
      if (json.progress < 100 && json.status !== 'failed') {
        timer = setTimeout(tick, interval);
      }
    }
    tick();
    return () => clearTimeout(timer);
  }, [url]);

  return data; // {progress, status, …}
}
```

### UX
* Плавно анимируйте прогресс-бар между полученными значениями.
* Обрабатывайте `failed`: показывайте ошибку и кнопку **Retry**.
* При перезагрузке страницы восстанавливайте состояния через `…/status`.

---

## 5. Запуск backend в Docker
```bash
cd backend
# первый запуск — поднять БД + Redis
docker compose up -d db redis
# применить миграции (progress columns)
alembic upgrade head
# запустить backend и Celery
docker compose up -d backend celery
```
Проверьте `curl http://localhost:8000/health` → 200.

---

Документация актуальна для коммита с миграцией `e1b2c3d4e5f6` (progress). 