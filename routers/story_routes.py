from fastapi import APIRouter, Depends, HTTPException, status
from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
import logging
import uuid

from utils.celery_app import celery_app
from utils.auth import get_current_active_user
from schemas.story_schemas import (
    StoryCreateRequest, StoryStatusResponse, StoryResultResponse,
    StoryListResponse, StoryItemResponse
)
from db.avatar_repository import User, Story, StoryStatus, get_db

# Import Celery task lazily to avoid issues
from tasks.agent_tasks import generate_story

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stories/", status_code=status.HTTP_202_ACCEPTED, response_model=StoryStatusResponse)
async def create_story_generation(
    request: StoryCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> StoryStatusResponse:
    """Enqueue a new story generation job (Multi-Agent pipeline).

    Returns Celery task ID so the client can poll for status/result.
    """
    try:
        logger.info("User %s requested story generation: %s", current_user.username, request)
        
        # Start Celery task
        async_result = generate_story.delay(request.dict())
        
        # Save story to database
        story = Story(
            user_id=current_user.id,
            title=request.theme or "Новая история",
            prompt=request.prompt,
            genre=request.genre,
            style=request.style,
            theme=request.theme,
            book_style=request.book_style,
            wishes=request.wishes,
            task_id=async_result.id,
            status=StoryStatus.PENDING
        )
        
        db.add(story)
        await db.commit()
        await db.refresh(story)
        
        logger.info("Created story record %s for user %s", story.id, current_user.username)
        
        return StoryStatusResponse(task_id=async_result.id, status="PENDING")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to enqueue story generation task: %s", e)
        raise HTTPException(status_code=500, detail="Failed to enqueue story generation task")


@router.get("/stories/{task_id}", response_model=StoryResultResponse | StoryStatusResponse)
async def get_story_generation_result(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> StoryResultResponse | StoryStatusResponse:
    """Get status or final result for a story generation Celery task."""
    try:
        # Check if user owns this story
        story_query = select(Story).where(
            Story.task_id == task_id,
            Story.user_id == current_user.id
        )
        story_result = await db.execute(story_query)
        story = story_result.scalar_one_or_none()
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or doesn't belong to current user"
            )
        
        async_result = AsyncResult(task_id, app=celery_app)
        status_str = async_result.status

        if async_result.successful():
            result_data = async_result.result or {}
            logger.info("Story generation %s completed for user %s", task_id, current_user.username)
            
            # Update story in database
            update_stmt = update(Story).where(Story.task_id == task_id).values(
                status=StoryStatus.COMPLETED,
                story_data=result_data
            )
            await db.execute(update_stmt)
            await db.commit()
            
            # Expecting dict with keys: script, style, characters, environments
            return StoryResultResponse(
                task_id=task_id,
                status="SUCCESS",
                script=result_data.get("script", {}),
                style=result_data.get("style", {}),
                characters=result_data.get("characters", {}),
                environments=result_data.get("environments", {}),
                illustrations=result_data.get("illustrations", {}),
            )
        elif async_result.failed():
            logger.warning("Story generation %s failed", task_id)
            
            # Update story status to failed
            update_stmt = update(Story).where(Story.task_id == task_id).values(
                status=StoryStatus.FAILED
            )
            await db.execute(update_stmt)
            await db.commit()
            
            return StoryStatusResponse(task_id=task_id, status="FAILURE", error=str(async_result.result))
        else:
            # PENDING, STARTED or RETRY
            # Update story status to in_progress if started
            if status_str in ["STARTED", "RETRY"]:
                update_stmt = update(Story).where(Story.task_id == task_id).values(
                    status=StoryStatus.IN_PROGRESS
                )
                await db.execute(update_stmt)
                await db.commit()
            
            return StoryStatusResponse(task_id=task_id, status=status_str)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching status for %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stories/", response_model=StoryListResponse)
async def list_user_stories(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> StoryListResponse:
    """Get list of all stories created by the current user."""
    try:
        stories_query = select(Story).where(
            Story.user_id == current_user.id
        ).order_by(Story.created_at.desc())
        
        result = await db.execute(stories_query)
        stories = result.scalars().all()
        
        story_items = []
        for story in stories:
            # Extract preview from story_data if available
            preview_text = None
            if story.story_data and isinstance(story.story_data, dict):
                script = story.story_data.get("script", {})
                if script and script.get("pages"):
                    # Get first page text as preview
                    first_page = script["pages"][0] if script["pages"] else {}
                    preview_text = first_page.get("text", "")[:150] + "..." if first_page.get("text") else None
            
            story_items.append(StoryItemResponse(
                id=story.id,
                title=story.title or "Без названия",
                theme=story.theme,
                genre=story.genre,
                style=story.style,
                status=story.status.value,
                preview_text=preview_text,
                created_at=story.created_at,
                task_id=story.task_id
            ))
        
        return StoryListResponse(stories=story_items)
        
    except Exception as e:
        logger.exception("Error getting stories for user %s: %s", current_user.id, e)
        raise HTTPException(status_code=500, detail="Internal server error") 