# ToonzyAI Backend – Endpoint Reference (Detailed)

This reference describes **every active REST endpoint** of the ToonzyAI backend, including sample requests, responses, validation rules, and common error codes.

Base URL (local):
```text
http://localhost:8000/api/v1
```
All endpoints below are relative to that prefix.

Legend
• 🔒 Auth required (`Authorization: Bearer <access_token>`).  
• ⏳ Long-running – poll status endpoints for completion.  
• 🖼️ Media stream – supports HTTP `Range` requests for `<video>` / `<audio>` tags.

---

## 0. Authentication

| Method | Path | Body | Response | Notes |
| ------ | ---- | ---- | -------- | ----- |
| POST | `/auth/login` | `{ "username": "demo", "password": "secret" }` | `{ "access_token": "…", "refresh_token": "…", "token_type": "bearer" }` | Access TTL 15 min, refresh TTL 7 days |
| POST | `/auth/refresh` | `{ "refresh_token": "…" }` | `{ "access_token": "…", "token_type": "bearer" }` | Issue new access token |

---

## 1. Avatars – Google Vertex AI Imagen

### 1.1 Create Avatar
```bash
curl -X POST \  
     -H "Authorization: Bearer $TOKEN" \  
     -H "Content-Type: application/json" \  
     -d '{"prompt":"A cute cartoon cat"}' \  
     $BASE/avatars/
```
Response `201 Created`
```jsonc
{
  "id": "5b493d5e-fcd9-4a3c-9304-bf125c889a90",
  "prompt": "A cute cartoon cat",
  "image_url": "https://storage.googleapis.com/toonzyai/avatars/5b49....jpg",
  "created_at": "2024-05-07T14:27:18.541Z"
}
```

### 1.2 List Avatars
`GET /avatars/` → array of the same objects.

### 1.3 Get / Delete Avatar
`GET /avatars/{avatar_id}`   `DELETE /avatars/{avatar_id}`

Validation rules
* `prompt` – 10-500 chars, safe-content only (see `CONTENT_FILTERING_GUIDE.md`).

---

## 2. Animation Projects

### 2.1 Create Project
Request
```jsonc
POST /animations/
{
  "source_avatar_id": "5b493d5e-fcd9-4a3c-9304-bf125c889a90",
  "total_segments": 5,            // 1-10
  "animation_prompt": "Cat performs various actions"
}
```
Important validation
* `total_segments` 1-10.
* Avatar must belong to caller.

Response `202 Accepted`
```jsonc
{
  "id": "a1b2…",
  "status": "PENDING",
  "segments": [ /* 5 elements, all PENDING */ ]
}
```
A Celery task (`create_animation_segments_task`) immediately inserts **N** segments; each starts with:
```json
{ "status": "PENDING", "progress": 0 }
```

### 2.2 Project List / Detail
`GET /animations/` – summary list.  
`GET /animations/{id}` – full detail including nested segment objects (see schema § 4).  
Fields always include `progress` (0-100).

### 2.3 Delete Project
`DELETE /animations/{id}` → `204 No Content` – cascade deletes segments in DB and media files in GCS.

### 2.4 Assemble Final Video ⏳
`POST /animations/{id}/assemble` 
* Pre-condition: every segment `COMPLETED`.
* Celery task stitches mp4s with `ffmpeg`.  
* Until done `status` of project = `IN_PROGRESS`.

### 2.5 Stream Final Video 🖼️
`GET /animations/{id}/video`  
Headers returned when full content:
```
Content-Type: video/mp4
Accept-Ranges: bytes
Content-Length: …
```
If the client sends `Range: bytes=…` partial content `206` is served.

---

## 3. Segment-level Operations

### 3.1 Batch Prompt Update
`PUT /animations/{id}/segments/prompts`
```jsonc
{
  "prompts": [
    { "segment_number": 1, "segment_prompt": "Cat yawns" },
    { "segment_number": 2, "segment_prompt": "Cat jumps" }
  ]
}
```
* All prompts must be ≥ 10 chars.  
* Fails `400` if any listed segment is `IN_PROGRESS`.

### 3.2 Parallel Generation ⏳
`POST /animations/{id}/segments/generate-all`
```jsonc
{ "force_regenerate": false }
```
Response `202` example
```jsonc
{
  "message": "🚀 Started parallel generation for 5 segments!",
  "task_ids": ["249b…", "19e4…"],
  "status": "generating"
}
```
What happens:
1. Backend sets each eligible segment `status=IN_PROGRESS` & `progress=0`.  
2. Spawns **N** Celery tasks (`generate_segment_task`).  
3. Each task:
   * Uploads avatar as start frame.  
   * Calls Google Veo 2.0 LRO.  
   * Updates `progress` 10→30→90→100.  
   * On success `generated_video_url` is set and status → `COMPLETED`.

### 3.3 Single Segment Generation ⏳
`POST /animations/{id}/segments/{n}/generate`
```jsonc
{ "segment_prompt": "Cat dances" }
```
Used for:
* Regenerating **FAILED/COMPLETED** segments.  
* Experimental per-segment creative iterations.

### 3.4 Segment Status
`GET /animations/{id}/segments/{n}` – sample response
```jsonc
{
  "segment_number": 3,
  "status": "IN_PROGRESS",
  "progress": 42,
  "actions": {
    "generate_endpoint": "/animations/a1b2/segments/3/generate",
    "batch_prompt_endpoint": "/animations/a1b2/segments/prompts"
  }
}
```

### 3.5 Stream Segment Video 🖼️
`GET /animations/{id}/segments/{n}/video` – identical Range behaviour to final video.

---

## 4. Status Enumeration
```
PENDING      – not generated yet
IN_PROGRESS  – Celery task actively running
COMPLETED    – video ready
FAILED       – generation errored (retry possible)
```

`progress` field (0-100) roughly correlates to pipeline stages:  
0–10 % DB updates → 30 % avatar upload → 90 % Veo finished → 100 % DB commit.

---

## 5. Error Codes
| Status | Meaning | Typical Causes |
| ------ | ------- | -------------- |
| 400    | Business rule violated | Missing prompts, segment busy, force_regenerate=false |
| 404    | Entity not found | Bad UUID, video not ready |
| 422    | Validation error (Pydantic) | prompt < 10 chars |
| 503    | Upstream error | Google Veo / GCS unreachable |

Error payload example
```jsonc
{
  "detail": "Segments [2] don't have prompts. Set prompts first using /segments/prompts endpoint."
}
```

---

## 6. Curl Cheat-Sheet
```bash
# 1) Login
TOKEN=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"secret"}' \
  $BASE/auth/login | jq -r .access_token)

# 2) Generate avatar
AVATAR=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -d '{"prompt":"Cartoon cat"}' $BASE/avatars/ | jq -r .id)

# 3) Create project
PROJ=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -d "{\"source_avatar_id\":\"$AVATAR\",\"total_segments\":5,\"animation_prompt\":\"Cat adventures\"}" \
  $BASE/animations/ | jq -r .id)
```
…etc. (complete script in `PARALLEL_GENERATION_GUIDE.md`).

---

## 7. Internal Implementation Notes
* All DB access through `SQLAlchemy 2.0 + asyncpg`.
* Celery worker uses `asyncio` loop patch (see `ASYNC_EVENT_LOOP_FIX.md`).
* Media on Google Cloud Storage; URL conversion via `utils.gcs_client.get_public_url`.
* No signed-URL flow – direct proxy streaming for simplicity.

---
© ToonzyAI 2024 – Version v1.3 (Async-only, Parallel Gen) 