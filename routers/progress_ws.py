from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import logging
from uuid import UUID

from db.avatar_repository import get_db, Avatar, AnimationSegment, AnimationProject, AnimationStatus
from utils.auth import get_current_active_user, verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

async def _fetch_progress_with_fresh_session(entity_type: str, entity_id: UUID):
    """Fetch progress with a fresh database session to see latest updates."""
    from db.avatar_repository import AsyncSessionLocal
    
    async with AsyncSessionLocal() as fresh_db:
        if entity_type == "avatar":
            q = await fresh_db.execute(select(Avatar).where(Avatar.id == entity_id))
            obj = q.scalar_one_or_none()
        elif entity_type == "segment":
            q = await fresh_db.execute(select(AnimationSegment).where(AnimationSegment.id == entity_id))
            obj = q.scalar_one_or_none()
        elif entity_type == "project":
            q = await fresh_db.execute(select(AnimationProject).where(AnimationProject.id == entity_id))
            obj = q.scalar_one_or_none()
        else:
            obj = None
        return obj

@router.websocket("/progress/{entity_type}/{entity_id}")
async def ws_progress(websocket: WebSocket, entity_type: str, entity_id: str, db: AsyncSession = Depends(get_db)):
    """WebSocket, который шлёт JSON-объекты с прогрессом каждый 2 секунды.
    entity_type: avatar | segment | project
    entity_id: UUID строки
    Авторизация через query-параметр ?token=...  (Bearer не передаётся в WS)."""
    
    logger.info(f"WebSocket connection attempt: {entity_type}/{entity_id}")
    logger.info(f"Query params: {dict(websocket.query_params)}")
    
    try:
        await websocket.accept()
        logger.info("WebSocket accepted successfully")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket: {e}")
        return

    # simple token auth via query param
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("No token provided in query params")
        await websocket.close(code=4401)
        return
    
    logger.info(f"Token received: {token[:50]}...")
    
    try:
        payload = verify_token(token, "access")
        if not payload:
            logger.warning("Token verification failed")
            await websocket.close(code=4401)
            return
        logger.info(f"Token verified successfully for user: {payload.username}")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        await websocket.close(code=4401)
        return

    try:
        uuid_val = UUID(entity_id)
        logger.info(f"UUID parsed successfully: {uuid_val}")
    except Exception as e:
        logger.error(f"Invalid UUID format: {entity_id}, error: {e}")
        await websocket.close(code=4400)
        return

    try:
        while True:
            # Use fresh session for each check to see latest updates
            obj = await _fetch_progress_with_fresh_session(entity_type, uuid_val)
            if not obj:
                await websocket.send_json({"error": "not_found"})
                await websocket.close(code=4404)
                break

            # Build progress dict
            if entity_type == "avatar":
                data = {
                    "id": str(obj.id),
                    "status": obj.status,
                    "progress": getattr(obj, "progress", 0)
                }
                done = obj.status in ["completed", "failed"]
                logger.info(f"Avatar {entity_id} progress: {data['progress']}%, status: {data['status']}")
            elif entity_type == "segment":
                data = {
                    "id": str(obj.id),
                    "status": obj.status.value if isinstance(obj.status, AnimationStatus) else obj.status,
                    "progress": getattr(obj, "progress", 0)
                }
                done = obj.status in [AnimationStatus.COMPLETED, AnimationStatus.FAILED]
                logger.info(f"Segment {entity_id} progress: {data['progress']}%, status: {data['status']}")
            else:  # project
                total = obj.total_segments
                completed = len([s for s in obj.segments if s.status == AnimationStatus.COMPLETED]) if hasattr(obj, "segments") else 0
                percent = int((completed / total) * 100) if total else 0
                data = {
                    "id": str(obj.id),
                    "status": obj.status.value if isinstance(obj.status, AnimationStatus) else obj.status,
                    "completed": completed,
                    "total": total,
                    "progress": percent
                }
                done = obj.status in [AnimationStatus.COMPLETED, AnimationStatus.FAILED]
                logger.info(f"Project {entity_id} progress: {completed}/{total} segments completed, status: {data['status']}")

            await websocket.send_json(data)
            if done:
                logger.info(f"Task {entity_type} {entity_id} completed, closing WebSocket")
                await asyncio.sleep(1)
                await websocket.close()
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for %s %s", entity_type, entity_id) 