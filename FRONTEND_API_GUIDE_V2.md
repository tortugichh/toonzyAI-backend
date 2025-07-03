# Toonzy AI – Frontend API Guide (v2)

> Актуально после упрощения backend-маршрутов (обязательный `segment_prompt`, удалены signed-url и др.).

---

## 0. Быстрый старт
1. Запустите backend:  `docker compose up -d backend celery db redis`  
2. В Vite-фронте пропишите proxy: `/api → http://localhost:8000`.  
3. Авторизация = JWT:  `/auth/register` → `/auth/token`.  
4. Основной flow:  **аватар → проект → сегменты → видео**.  
5. Файлы хранятся в публичном GCS-бакете ⇒ URL-ы уже публичные.

---

## 1. Авторизация (JWT)
| Действие | Method | Путь |
|----------|--------|------|
| Регистрация | POST | `/api/v1/auth/register` |
| Получить токен | POST | `/api/v1/auth/token` |
| Обновить токен | POST | `/api/v1/auth/refresh` |

Добавляйте во все запросы:  
`Authorization: Bearer <access_token>`

---

## 2. Аватары
| Действие | Method | Путь |
|----------|--------|------|
| Создать | POST | `/api/v1/avatars/` |
| Статус  | GET  | `/api/v1/avatars/{id}/status` |
| Картинка| GET  | `/api/v1/avatars/{id}/image` |
| Список  | GET  | `/api/v1/avatars/?page=1&per_page=10` |
| Удалить | DELETE | `/api/v1/avatars/{id}` |

После создания аватара полльте `…/status` до `progress == 100 && status == completed`, затем грузите `…/image`.

---

## 3. Анимация
### 3.1 Создать проект
`POST /api/v1/animations/`
```jsonc
{
  "source_avatar_id": "<UUID>",
  "total_segments": 3,
  "animation_prompt": "(необязательно) общий фоновой промпт"
}
```
Ответ вернёт `project_id` и сегменты (`status=pending`).

### 3.2 Работа с сегментами
| Действие | Method | Путь |
|----------|--------|------|
| Получить проект | GET | `/api/v1/animations/{project_id}` |
| Запустить сегмент | POST | `/api/v1/animations/{project_id}/segments/{n}/generate` |
| Детали сегмента   | GET  | `/api/v1/animations/{project_id}/segments/{n}` |
| Видео сегмента    | GET  | `/api/v1/animations/{project_id}/segments/{n}/video` |
| Финальное видео   | GET  | `/api/v1/animations/{project_id}/video` |
| Сборка финала     | POST | `/api/v1/animations/{project_id}/assemble` |
| Удалить проект    | DELETE | `/api/v1/animations/{project_id}` |

#### 3.2.1 Запуск генерации сегмента
```http
POST /api/v1/animations/{id}/segments/1/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "segment_prompt": "A cyberpunk cat jumps over neon rooftops"
}
```
Ответ:
```jsonc
{
  "message": "Segment generation started successfully!",
  "status": "in_progress",
  "task_id": "<celery_uuid>",
  "monitoring": {
    "status_endpoint": "/api/v1/animations/{id}/segments/1"
  }
}
```

#### 3.2.2 Polling статуса
```ts
const { progress, status, video_url } = useProgress(`/api/v1/animations/${id}/segments/${n}`);
```
Ступени прогресса: `10 → 30 → 90 → 100`.

При `status == completed` → `video_url` доступно:  
`<video src={video_url} controls />`

---

## 4. Прогресс-бар API
| Сущность | Шаги |
|----------|------|
| Avatar   | 10, 50, 80, 100 |
| Segment  | 10, 30, 90, 100 |

Поле `status`: `pending`, `in_progress`, `completed`, `failed`.

---

## 5. React-хуки примеры
### 5.1 useProgress
```ts
export function useProgress(url: string, interval = 2000) {
  const [data, setData] = useState<any>();

  useEffect(() => {
    const id = setInterval(async () => {
      const res = await fetch(url, { headers: authHeader() });
      setData(await res.json());
    }, interval);
    return () => clearInterval(id);
  }, [url]);

  return data;
}
```

### 5.2 Кнопка генерации сегмента
```tsx
function SegmentGenerate({ projectId, number }: { projectId: string; number: number }) {
  const [prompt, setPrompt] = useState('');

  const generate = async () => {
    await fetch(`/api/v1/animations/${projectId}/segments/${number}/generate`, {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ segment_prompt: prompt }),
    });
  };

  return (
    <div>
      <textarea value={prompt} onChange={e => setPrompt(e.target.value)} />
      <button onClick={generate}>Generate segment {number}</button>
    </div>
  );
}
```

---

## 6. Ошибки
| Код | Причина |
|-----|---------|
| 400 | отсутствует prompt / неверный статус |
| 401 | токен отсутствует или истёк |
| 403 | объект не принадлежит пользователю |
| 404 | id не найден |
| 409 | сегмент уже генерируется |
| 500 | внутренняя ошибка |

---

## 7. Deployment / Ops
* GCS-bucket public → прямые HTTPS-URL-ы; backend вернёт signed URL только если bucket станет приватным.
* `docker compose scale celery=4` — горизонтальное масштабирование генерации.
* Добавьте `?cacheBust=${Date.now()}` к `video_url` при повторной генерации, если CDN кеширует предыдущую версию.

---

Happy coding & stay creative! 🎬
