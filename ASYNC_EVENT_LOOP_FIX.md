# AsyncIO Event Loop Fix - Celery Workers

## Problem Summary

The ToonzyAI backend was experiencing **asyncio event loop conflicts** in Celery workers, causing tasks to fail with errors like:

```
RuntimeError: Event loop is closed
Task got Future attached to a different loop
Exception terminating connection <AdaptedConnection>
```

## Root Cause

The issue was in `tasks/generation_tasks.py` where **`asyncio.run()`** was being called inside Celery tasks:

```python
# ❌ PROBLEMATIC CODE
@celery_app.task(name="tasks.generation_tasks.generate_segment_task", bind=True, max_retries=3)
def generate_segment_task(self, project_id: str, segment_number: int):
    # This creates a new event loop, conflicting with Celery's loop management
    result = asyncio.run(_generate_segment_async(UUID(project_id), segment_number))
```

### Why This Failed

1. **Celery workers** run in their own process/thread context
2. **`asyncio.run()`** tries to create a completely new event loop
3. **Database connections** (AsyncPG) get attached to the wrong loop
4. When the task completes, connections try to close in a **different/closed loop**

## Solution Applied

### ✅ Fixed Event Loop Management

```python
# ✅ FIXED CODE
@celery_app.task(name="tasks.generation_tasks.generate_segment_task", bind=True, max_retries=3)
def generate_segment_task(self, project_id: str, segment_number: int):
    try:
        # Правильное управление event loop в Celery
        try:
            # Пытаемся получить текущий event loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                # Если loop закрыт, создаем новый
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # Если нет event loop, создаем новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Запускаем асинхронную функцию в правильном контексте
        result = loop.run_until_complete(_generate_segment_async(UUID(project_id), segment_number))
        
        return result
    except Exception as e:
        # Retry logic...
```

### Key Improvements

1. **Check existing loop**: Tries to use existing event loop if available
2. **Handle closed loops**: Creates new loop if current one is closed
3. **Proper loop setting**: Sets the loop as the current thread's loop
4. **Use `run_until_complete()`**: Instead of `asyncio.run()` for Celery compatibility

## Database Session Configuration

The fix also leverages properly configured **async database sessions** for Celery:

```python
# Отдельный движок для задач Celery с собственным connection pool
celery_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    # Изоляция для каждого процесса
    connect_args={
        "server_settings": {
            "application_name": "celery_worker",
        }
    }
)

# Сессия для Celery задач
CeleryAsyncSession = sessionmaker(
    celery_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)
```

## Testing the Fix

### 1. Restart Celery Worker
```bash
docker compose restart celery
```

### 2. Monitor Logs
```bash
docker compose logs celery -f
```

### 3. Test Video Generation
```bash
curl -X POST "http://localhost:8000/api/v1/animations/{project_id}/segments/{segment_number}/generate" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"segment_prompt": "A cat sitting peacefully on a windowsill"}'
```

## Expected Results

### ✅ Before Fix (Errors)
```
[ERROR] RuntimeError: Event loop is closed
[ERROR] Task got Future attached to a different loop
[ERROR] Exception terminating connection
```

### ✅ After Fix (Success)
```
[INFO] 🎬 Starting segment generation task: project abc123, segment 1
[INFO] Starting generation for project abc123, segment 1
[INFO] ✅ Completed generation for segment 1
```

## Additional Benefits

1. **Stable database connections**: No more connection termination errors
2. **Reliable task execution**: Tasks can retry without event loop conflicts
3. **Better error handling**: Clean separation between async/sync contexts
4. **Improved logging**: Clearer task progress tracking

## Related Issues Fixed

- **Database connection pooling** in async context
- **Vertex AI client** async operations in Celery
- **GCS upload/download** operations in background tasks
- **FFmpeg frame extraction** in async workflows

## Best Practices Applied

1. **Never use `asyncio.run()` in Celery tasks**
2. **Always check/create event loops properly**
3. **Use dedicated database engines for Celery**
4. **Handle async/sync boundaries carefully**
5. **Test async operations in Celery context**

This fix ensures stable, reliable video generation processing in the ToonzyAI backend! 