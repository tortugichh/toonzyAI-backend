from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional, Iterator
import logging
import httpx
import asyncio
from io import BytesIO
import re

from db.avatar_repository import (
    get_db, 
    AnimationProject, 
    AnimationSegment, 
    AnimationStatus,
    Avatar,
    User
)
from schemas.animation_schemas import (
    AnimationProjectCreate,
    AnimationProjectResponse,
    AnimationProjectListResponse,
    AssembleVideoResponse,
    SegmentGenerateRequest,
    BatchSegmentPromptsUpdate,
    GenerateAllSegmentsRequest,
    BatchGenerationResponse
)
from utils.auth import get_current_active_user
from utils.gcs_client import get_public_url, download_file_from_gcs_authenticated, get_file_size_from_gcs
# Import tasks only when needed to avoid circular imports at startup

router = APIRouter()
logger = logging.getLogger(__name__)


def parse_range_header(range_header: str, content_length: int) -> tuple[int, int]:
    """
    Парсит HTTP Range заголовок и возвращает start, end позиции.
    """
    if not range_header.startswith('bytes='):
        raise ValueError("Invalid range header")
    
    range_spec = range_header[6:]  # Remove 'bytes='
    
    if '-' not in range_spec:
        raise ValueError("Invalid range format")
    
    start_str, end_str = range_spec.split('-', 1)
    
    if start_str:
        start = int(start_str)
    else:
        start = 0
    
    if end_str:
        end = int(end_str)
    else:
        end = content_length - 1
    
    # Ensure valid range
    start = max(0, start)
    end = min(content_length - 1, end)
    
    return start, end


def create_video_stream(video_data: bytes, start: int = 0, end: Optional[int] = None, chunk_size: int = 8192) -> Iterator[bytes]:
    """
    Создает итератор для потоковой передачи видео с поддержкой Range requests.
    """
    if end is None:
        end = len(video_data)
    
    current_pos = start
    
    while current_pos < end:
        chunk_end = min(current_pos + chunk_size, end)
        chunk = video_data[current_pos:chunk_end]
        yield chunk
        current_pos = chunk_end


@router.post("/", status_code=status.HTTP_202_ACCEPTED, response_model=AnimationProjectResponse)
async def create_animation_project(
    project_data: AnimationProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AnimationProjectResponse:
    """
    Создает новый проект анимации и запускает генерацию сегментов.
    """
    try:
        # 1. Проверяем, что аватар принадлежит текущему пользователю
        avatar_query = select(Avatar).where(
            Avatar.id == project_data.source_avatar_id,
            Avatar.user_id == current_user.id
        )
        avatar_result = await db.execute(avatar_query)
        avatar = avatar_result.scalar_one_or_none()
        
        if not avatar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found or doesn't belong to current user"
            )
        
        # 2. Создаем проект анимации
        animation_project = AnimationProject(
            user_id=current_user.id,
            source_avatar_id=project_data.source_avatar_id,
            total_segments=project_data.total_segments,
            animation_prompt=project_data.animation_prompt,
            status=AnimationStatus.PENDING
        )
        
        db.add(animation_project)
        await db.commit()
        await db.refresh(animation_project)
        
        # 3. Запускаем фоновую задачу создания сегментов
        from tasks.generation_tasks import create_animation_segments_task
        create_animation_segments_task.delay(str(animation_project.id))
        
        logger.info(f"Created animation project {animation_project.id} for user {current_user.id}")
        
        # 4. Возвращаем созданный проект
        return AnimationProjectResponse(
            id=animation_project.id,
            user_id=animation_project.user_id,
            source_avatar_id=animation_project.source_avatar_id,
            total_segments=animation_project.total_segments,
            animation_prompt=animation_project.animation_prompt,
            status=animation_project.status,
            final_video_url=animation_project.final_video_url,
            video_url=f"/api/v1/animations/{animation_project.id}/video" if animation_project.final_video_url else None,
            created_at=animation_project.created_at,
            updated_at=animation_project.updated_at,
            segments=[]  # Сегменты будут созданы асинхронно
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating animation project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create animation project"
        )


@router.get("/{project_id}", response_model=AnimationProjectResponse)
async def get_animation_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AnimationProjectResponse:
    """
    Получает статус проекта анимации и всех его сегментов.
    """
    try:
        # Получаем проект с сегментами
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Получаем сегменты
        segments_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id
        ).order_by(AnimationSegment.segment_number)
        segments_result = await db.execute(segments_query)
        segments = segments_result.scalars().all()
        
        return AnimationProjectResponse(
            id=project.id,
            user_id=project.user_id,
            source_avatar_id=project.source_avatar_id,
            total_segments=project.total_segments,
            animation_prompt=project.animation_prompt,
            status=project.status,
            final_video_url=project.final_video_url,
            video_url=f"/api/v1/animations/{project.id}/video" if project.final_video_url else None,
            created_at=project.created_at,
            updated_at=project.updated_at,
            segments=[
                {
                    "id": segment.id,
                    "segment_number": segment.segment_number,
                    "status": segment.status,
                    "start_frame_url": segment.start_frame_url,
                    "generated_video_url": segment.generated_video_url,
                    "video_url": f"/api/v1/animations/{project_id}/segments/{segment.segment_number}/video" if segment.generated_video_url else None,
                    "created_at": segment.created_at,
                    "updated_at": segment.updated_at
                }
                for segment in segments
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting animation project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get animation project"
        )


@router.get("/", response_model=List[AnimationProjectListResponse])
async def list_animation_projects(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[AnimationProjectListResponse]:
    """
    Получает список всех проектов анимации пользователя.
    """
    try:
        projects_query = select(AnimationProject).where(
            AnimationProject.user_id == current_user.id
        ).order_by(AnimationProject.created_at.desc())
        
        projects_result = await db.execute(projects_query)
        projects = projects_result.scalars().all()
        
        return [
            AnimationProjectListResponse(
                id=project.id,
                source_avatar_id=project.source_avatar_id,
                animation_prompt=project.animation_prompt,
                status=project.status,
                total_segments=project.total_segments,
                final_video_url=project.final_video_url,
                video_url=f"/api/v1/animations/{project.id}/video" if project.final_video_url else None,
                created_at=project.created_at
            )
            for project in projects
        ]
        
    except Exception as e:
        logger.error(f"Error listing animation projects for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list animation projects"
        )


@router.post("/{project_id}/assemble", response_model=AssembleVideoResponse)
async def trigger_video_assembly(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AssembleVideoResponse:
    """
    Принудительно запускает сборку финального видео (если все сегменты готовы).
    """
    try:
        # Проверяем, что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Проверяем статус проекта
        if project.status == AnimationStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video already assembled"
            )
        
        if project.status == AnimationStatus.ASSEMBLING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video assembly already in progress"
            )
        
        # Проверяем готовность сегментов
        completed_segments_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id,
            AnimationSegment.status == AnimationStatus.COMPLETED
        )
        completed_segments_result = await db.execute(completed_segments_query)
        completed_segments = completed_segments_result.scalars().all()
        
        if len(completed_segments) != project.total_segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not all segments are ready. {len(completed_segments)}/{project.total_segments} completed"
            )
        
        # Запускаем сборку видео
        from tasks.assembly_tasks import assemble_video_task
        assemble_video_task.delay(str(project_id))
        
        logger.info(f"Triggered video assembly for project {project_id}")
        
        return AssembleVideoResponse(
            message="Video assembly started",
            project_id=project_id,
            status="assembling"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering assembly for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start video assembly"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_animation_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаляет проект анимации и все связанные сегменты.
    """
    try:
        # Проверяем, что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Удаляем проект (каскадное удаление удалит и сегменты)
        await db.delete(project)
        await db.commit()
        
        logger.info(f"Deleted animation project {project_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting animation project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete animation project"
        )


@router.get("/{project_id}/video")
async def get_animation_video(
    project_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает финальное видео анимации для просмотра с поддержкой Range requests.
    """
    try:
        # Получаем проект анимации
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        if not project.final_video_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation video is not ready yet"
            )
        
        # Загружаем видео из GCS с аутентификацией
        try:
            video_data = await download_file_from_gcs_authenticated(project.final_video_url)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation video file not found in storage"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve animation video: {e}"
            )
        content_length = len(video_data)
        
        # Проверяем Range заголовок для прогресса загрузки
        range_header = request.headers.get('range')
        
        if range_header:
            try:
                start, end = parse_range_header(range_header, content_length)
                content_range = f"bytes {start}-{end}/{content_length}"
                
                # Возвращаем частичный контент (206)
                return StreamingResponse(
                    create_video_stream(video_data, start, end + 1),
                    status_code=206,
                    media_type="video/mp4",
                    headers={
                        "Content-Range": content_range,
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(end - start + 1),
                        "Content-Disposition": f"inline; filename=animation_{project_id}.mp4",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            except ValueError:
                # Неверный Range заголовок, игнорируем
                pass
        
        # Обычная загрузка с поддержкой прогресса
        return StreamingResponse(
            create_video_stream(video_data),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Disposition": f"inline; filename=animation_{project_id}.mp4",
                "Cache-Control": "public, max-age=3600",
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting animation video {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get animation video"
        )


@router.get("/{project_id}/segments/{segment_number}/video")
async def get_segment_video(
    project_id: UUID,
    segment_number: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает видео конкретного сегмента анимации.
    """
    try:
        # Проверяем что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Получаем сегмент
        segment_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id,
            AnimationSegment.segment_number == segment_number
        )
        segment_result = await db.execute(segment_query)
        segment = segment_result.scalar_one_or_none()
        
        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_number} not found"
            )
        
        if not segment.generated_video_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_number} video is not ready yet"
            )
        
        # Загружаем видео из GCS с аутентификацией
        try:
            video_data = await download_file_from_gcs_authenticated(segment.generated_video_url)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Segment video file not found in storage"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve segment video: {e}"
            )
        content_length = len(video_data)
        
        # Проверяем Range заголовок для прогресса загрузки
        range_header = request.headers.get('range')
        
        if range_header:
            try:
                start, end = parse_range_header(range_header, content_length)
                content_range = f"bytes {start}-{end}/{content_length}"
                
                # Возвращаем частичный контент (206)
                return StreamingResponse(
                    create_video_stream(video_data, start, end + 1),
                    status_code=206,
                    media_type="video/mp4",
                    headers={
                        "Content-Range": content_range,
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(end - start + 1),
                        "Content-Disposition": f"inline; filename=segment_{segment_number}_{project_id}.mp4",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            except ValueError:
                # Неверный Range заголовок, игнорируем
                pass
        
        # Обычная загрузка с поддержкой прогресса
        return StreamingResponse(
            create_video_stream(video_data),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Disposition": f"inline; filename=segment_{segment_number}_{project_id}.mp4",
                "Cache-Control": "public, max-age=3600",
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting segment video {project_id}/{segment_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get segment video"
        )


# ==================== НОВЫЕ ЭНДПОИНТЫ ДЛЯ ПОЛЬЗОВАТЕЛЬСКОГО КОНТРОЛЯ СЕГМЕНТОВ ====================

@router.post("/{project_id}/segments/{segment_number}/generate")
async def generate_specific_segment(
    project_id: UUID,
    segment_number: int,
    generate_data: SegmentGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🎬 ПОЛЬЗОВАТЕЛЬСКИЙ КОНТРОЛЬ: Запускает генерацию конкретного сегмента.
    Пользователь может генерировать каждый кадр когда захочет!
    """
    try:
        # Проверяем, что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Находим сегмент
        segment_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id,
            AnimationSegment.segment_number == segment_number
        )
        segment_result = await db.execute(segment_query)
        segment = segment_result.scalar_one_or_none()
        
        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_number} not found"
            )
        
        # Проверяем статус сегмента
        if segment.status == AnimationStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Segment already completed. Delete and recreate if you want to regenerate."
            )
        
        if segment.status == AnimationStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Segment generation already in progress"
            )
        
        # Обновляем (или задаём) индивидуальный промпт сегмента – обязателен
            segment.segment_prompt = generate_data.segment_prompt
            await db.commit()
        
        # Убеждаемся, что промпт сохранён
        if not segment.segment_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Segment prompt is required to start generation"
            )
        
        # Запускаем генерацию сегмента
        from tasks.generation_tasks import generate_segment_task
        task = generate_segment_task.delay(str(project_id), segment_number)
        
        # Обновляем статус сегмента на IN_PROGRESS
        segment.status = AnimationStatus.IN_PROGRESS
        await db.commit()
        await db.refresh(segment)
        
        logger.info(f"Started generation for segment {segment_number} in project {project_id}")
        logger.info(f"Task ID: {task.id}")
        logger.info(f"Using prompt: {segment.segment_prompt}")
        
        return {
            "message": "Segment generation started successfully! 🚀",
            "project_id": str(project_id),
            "segment_number": segment_number,
            "task_id": task.id,
            "status": "in_progress",
            "prompt_used": segment.segment_prompt,
            "estimated_time": "3-5 minutes",
            "current_time": "UTC now",
            "monitoring": {
                "status_endpoint": f"/api/v1/animations/{project_id}/segments/{segment_number}",
                "video_endpoint": f"/api/v1/animations/{project_id}/segments/{segment_number}/video",
                "poll_interval_seconds": 10
            },
            "details": {
                "generator": "Google Veo 2.0",
                "duration": "5 seconds",
                "quality": "1280x720",
                "user_control": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting segment generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start segment generation"
        )


@router.get("/{project_id}/segments/{segment_number}")
async def get_segment_details(
    project_id: UUID,
    segment_number: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    📊 ПОЛЬЗОВАТЕЛЬСКИЙ КОНТРОЛЬ: Получает детальную информацию о конкретном сегменте.
    """
    try:
        # Проверяем, что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Находим сегмент
        segment_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id,
            AnimationSegment.segment_number == segment_number
        )
        segment_result = await db.execute(segment_query)
        segment = segment_result.scalar_one_or_none()
        
        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_number} not found"
            )
        
        # Определяем используемый промпт: для каждого сегмента промпт обязателен
        active_prompt = segment.segment_prompt
        prompt_source = "custom"
        
        # Статистика и детали
        status_details = {
            "pending": "⏳ Segment ready for generation",
            "in_progress": "🔄 Video is being generated with Veo 2.0",
            "completed": "✅ Video generated successfully",
            "failed": "❌ Generation failed"
        }
        
        return {
            "id": str(segment.id),
            "segment_number": segment.segment_number,
            "status": segment.status.value,
            "status_description": status_details.get(segment.status.value, "Unknown status"),
            "prompts": {
                "active_prompt": active_prompt,
                "prompt_source": prompt_source,
                "segment_prompt": segment.segment_prompt
            },
            "generation": {
                "generator": "Google Veo 2.0",
                "duration": "5 seconds",
                "quality": "1280x720",
                "estimated_time": "3-5 minutes" if segment.status.value == "in_progress" else None
            },
            "urls": {
                "start_frame_url": segment.start_frame_url,
                "generated_video_url": segment.generated_video_url,
                "video_endpoint": f"/api/v1/animations/{project_id}/segments/{segment_number}/video" if segment.generated_video_url else None,
                "download_endpoint": f"/api/v1/animations/{project_id}/segments/{segment_number}/video" if segment.generated_video_url else None
            },
            "actions": {
                "can_regenerate": segment.status.value in ["completed", "failed"],
                "can_update_prompt": True,
                "generate_endpoint": f"/api/v1/animations/{project_id}/segments/{segment_number}/generate",
                "batch_prompt_endpoint": f"/api/v1/animations/{project_id}/segments/prompts"
            },
            "timestamps": {
                "created_at": segment.created_at.isoformat() if segment.created_at else None,
                "updated_at": segment.updated_at.isoformat() if segment.updated_at else None
            },
            "user_control": {
                "enabled": True,
                "description": "You control when this segment generates"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting segment details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get segment details"
        )


# ==================== BATCH OPERATIONS FOR PARALLEL GENERATION ====================

@router.put("/{project_id}/segments/prompts")
async def update_all_segment_prompts(
    project_id: UUID,
    prompts_data: BatchSegmentPromptsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🎯 BATCH OPERATION: Обновляет промпты для всех сегментов сразу.
    Позволяет пользователю задать индивидуальные промпты для каждого сегмента.
    """
    try:
        # Проверяем, что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Получаем все сегменты проекта
        segments_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id
        )
        segments_result = await db.execute(segments_query)
        existing_segments = {seg.segment_number: seg for seg in segments_result.scalars().all()}
        
        updated_segments = []
        
        # Обновляем промпты для каждого сегмента
        for prompt_data in prompts_data.prompts:
            segment_number = prompt_data.segment_number
            
            if segment_number not in existing_segments:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Segment {segment_number} not found"
                )
            
            segment = existing_segments[segment_number]
            
            # Проверяем, что сегмент не в процессе генерации
            if segment.status == AnimationStatus.IN_PROGRESS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update prompt for segment {segment_number} - generation in progress"
                )
            
            # Обновляем промпт
            segment.segment_prompt = prompt_data.segment_prompt
            updated_segments.append({
                "segment_number": segment_number,
                "prompt": prompt_data.segment_prompt,
                "status": segment.status.value
            })
        
        await db.commit()
        
        logger.info(f"Updated prompts for {len(updated_segments)} segments in project {project_id}")
        
        return {
            "message": f"Successfully updated prompts for {len(updated_segments)} segments",
            "project_id": str(project_id),
            "updated_segments": updated_segments,
            "next_step": "Use /generate-all endpoint to start parallel generation"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating segment prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update segment prompts"
        )


@router.post("/{project_id}/segments/generate-all", response_model=BatchGenerationResponse)
async def generate_all_segments_parallel(
    project_id: UUID,
    generate_data: GenerateAllSegmentsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> BatchGenerationResponse:
    """
    🚀 PARALLEL GENERATION: Запускает генерацию ВСЕХ сегментов одновременно!
    Все сегменты генерируются параллельно, независимо друг от друга.
    """
    try:
        # Проверяем, что проект принадлежит пользователю
        project_query = select(AnimationProject).where(
            AnimationProject.id == project_id,
            AnimationProject.user_id == current_user.id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation project not found"
            )
        
        # Получаем все сегменты проекта
        segments_query = select(AnimationSegment).where(
            AnimationSegment.animation_project_id == project_id
        ).order_by(AnimationSegment.segment_number)
        segments_result = await db.execute(segments_query)
        segments = segments_result.scalars().all()
        
        if not segments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No segments found for this project"
            )
        
        # Проверяем, что у всех сегментов есть промпты
        segments_without_prompts = [
            seg.segment_number for seg in segments 
            if not seg.segment_prompt or seg.segment_prompt.strip() == ""
        ]
        
        if segments_without_prompts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Segments {segments_without_prompts} don't have prompts. Set prompts first using /segments/prompts endpoint."
            )
        
        # Определяем какие сегменты нужно генерировать
        segments_to_generate = []
        
        for segment in segments:
            if segment.status == AnimationStatus.PENDING:
                segments_to_generate.append(segment)
            elif segment.status == AnimationStatus.FAILED:
                segments_to_generate.append(segment)
            elif segment.status == AnimationStatus.COMPLETED and generate_data.force_regenerate:
                segments_to_generate.append(segment)
            elif segment.status == AnimationStatus.IN_PROGRESS:
                # Пропускаем сегменты, которые уже генерируются
                continue
        
        if not segments_to_generate:
            completed_count = len([s for s in segments if s.status == AnimationStatus.COMPLETED])
            in_progress_count = len([s for s in segments if s.status == AnimationStatus.IN_PROGRESS])
            
            if completed_count == len(segments):
                message = "All segments are already completed. Use force_regenerate=true to regenerate."
            elif in_progress_count > 0:
                message = f"{in_progress_count} segments are already generating. Wait for completion or use individual endpoints."
            else:
                message = "No segments available for generation."
                
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Запускаем параллельную генерацию всех сегментов
        task_ids = []
        
        from tasks.generation_tasks import generate_segment_task
        
        for segment in segments_to_generate:
            # Обновляем статус на IN_PROGRESS
            segment.status = AnimationStatus.IN_PROGRESS
            segment.progress = 0
            
            # Запускаем задачу генерации
            task = generate_segment_task.delay(str(project_id), segment.segment_number)
            task_ids.append(task.id)
            
            logger.info(f"Started parallel generation for segment {segment.segment_number}, task: {task.id}")
        
        await db.commit()
        
        logger.info(f"Started parallel generation for {len(segments_to_generate)} segments in project {project_id}")
        
        return BatchGenerationResponse(
            message=f"🚀 Started parallel generation for {len(segments_to_generate)} segments!",
            project_id=project_id,
            total_segments=len(segments),
            segments_started=len(segments_to_generate),
            task_ids=task_ids,
            estimated_completion_time="3-5 minutes per segment (all running in parallel)",
            status="generating"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting parallel generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start parallel generation"
        )


# Deprecated / auxiliary endpoints removed to keep API surface minimal.