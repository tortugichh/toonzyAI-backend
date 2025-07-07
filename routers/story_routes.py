from fastapi import APIRouter, Depends, HTTPException, status
from celery.result import AsyncResult
import logging

from utils.celery_app import celery_app
from utils.auth import get_current_active_user
from schemas.story_schemas import StoryCreateRequest, StoryStatusResponse, StoryResultResponse
from db.avatar_repository import User  # Using existing User model for auth dependency

# Import Celery task lazily to avoid issues
from tasks.agent_tasks import generate_story

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stories/", status_code=status.HTTP_202_ACCEPTED, response_model=StoryStatusResponse)
async def create_story_generation(
    request: StoryCreateRequest,
    current_user: User = Depends(get_current_active_user)
) -> StoryStatusResponse:
    """Enqueue a new story generation job (Multi-Agent pipeline).

    Returns Celery task ID so the client can poll for status/result.
    """
    try:
        logger.info("User %s requested story generation: %s", current_user.username, request.prompt)
        async_result = generate_story.delay(request.prompt)
        return StoryStatusResponse(task_id=async_result.id, status="PENDING")
    except Exception as e:
        logger.exception("Failed to enqueue story generation task: %s", e)
        raise HTTPException(status_code=500, detail="Failed to enqueue story generation task")


@router.get("/stories/{task_id}", response_model=StoryResultResponse | StoryStatusResponse)
async def get_story_generation_result(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
) -> StoryResultResponse | StoryStatusResponse:
    """Get status or final result for a story generation Celery task."""
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        status_str = async_result.status

        if async_result.successful():
            result_data = async_result.result or {}
            logger.info("Story generation %s completed for user %s", task_id, current_user.username)
            # Expecting dict with keys: script, style, characters, environments
            return StoryResultResponse(
                task_id=task_id,
                status="SUCCESS",
                script=result_data.get("script", {}),
                style=result_data.get("style", {}),
                characters=result_data.get("characters", {}),
                environments=result_data.get("environments", {}),
            )
        elif async_result.failed():
            logger.warning("Story generation %s failed", task_id)
            return StoryStatusResponse(task_id=task_id, status="FAILURE", error=str(async_result.result))
        else:
            # PENDING, STARTED or RETRY
            return StoryStatusResponse(task_id=task_id, status=status_str)

    except Exception as e:
        logger.exception("Error fetching status for %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch task status") 