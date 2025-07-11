import asyncio
import tempfile
import os
from uuid import UUID
from typing import List
from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import logging

from utils.celery_app import celery_app
from utils.ffmpeg_utils import concatenate_videos, validate_video_file
from utils.gcs_client import upload_file_to_gcs, download_file_from_gcs
from db.avatar_repository import (
    AnimationProject, 
    AnimationSegment, 
    AnimationStatus,
)

logger = logging.getLogger(__name__)

# Создаем отдельный движок для Celery задач
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")

celery_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

CeleryAsyncSession = async_sessionmaker(
    celery_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@celery_app.task(bind=True, max_retries=2)
def assemble_video_task(self, project_id: str):
    """Celery task for assembling final video."""
    try:
        # Obtain or create a persistent event loop for this worker process
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(_assemble_video_async(UUID(project_id)))
        return result
            
    except Exception as exc:
        logger.error(f"Error in assemble_video_task: {exc}")
        # Update project status to FAILED (best-effort)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_update_project_status(UUID(project_id), AnimationStatus.FAILED))
        except Exception as status_err:
            logger.error(f"Failed to mark project as FAILED: {status_err}")
        
        # Retry with back-off
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        raise exc


async def _assemble_video_async(project_id: UUID) -> dict:
    """
    Асинхронная функция для сборки финального видео.
    """
    async with CeleryAsyncSession() as session:
        try:
            # 1. Получаем проект
            project_query = select(AnimationProject).where(AnimationProject.id == project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Animation project {project_id} not found")
            
            # 2. Обновляем статус проекта на ASSEMBLING
            project.status = AnimationStatus.ASSEMBLING
            await session.commit()
            
            logger.info(f"Starting video assembly for project {project_id}")
            
            # 3. Получаем все готовые сегменты в правильном порядке
            segments_query = select(AnimationSegment).where(
                AnimationSegment.animation_project_id == project_id,
                AnimationSegment.status == AnimationStatus.COMPLETED
            ).order_by(AnimationSegment.segment_number)
            
            segments_result = await session.execute(segments_query)
            segments = segments_result.scalars().all()
            
            if len(segments) != project.total_segments:
                raise ValueError(
                    f"Not all segments are ready. Expected {project.total_segments}, got {len(segments)}"
                )
            
            # 4. Скачиваем все видео-сегменты
            temp_video_paths = await _download_segments(segments)
            
            # 5. Валидируем все видеофайлы и логируем подробности
            for path in temp_video_paths:
                is_valid = validate_video_file(path)
                if is_valid:
                    logger.debug(f"✅ Video validated: {path}")
                else:
                    logger.error(f"❌ Invalid video file detected: {path}")
                    raise ValueError(f"Invalid video file: {path}")
            
            # 6. Собираем финальное видео
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as final_video:
                final_video_path = final_video.name
            
            logger.info(f"Concatenating {len(temp_video_paths)} video segments")
            try:
                concatenate_videos(temp_video_paths, final_video_path)
            except Exception as ffmpeg_err:
                logger.exception(f"FFmpeg concatenate_videos failed: {ffmpeg_err}")
                raise
            
            # 7. Загружаем финальное видео в GCS
            final_video_url = await upload_file_to_gcs(
                final_video_path,
                f"animations/final/{project_id}.mp4"
            )
            
            # 8. Обновляем проект с финальным URL
            project.final_video_url = final_video_url
            project.status = AnimationStatus.COMPLETED
            await session.commit()
            
            # 9. Очищаем временные файлы
            await _cleanup_temp_files(temp_video_paths + [final_video_path])
            
            logger.info(f"Successfully assembled video for project {project_id}: {final_video_url}")
            
            return {
                "status": "completed",
                "project_id": str(project_id),
                "final_video_url": final_video_url,
                "segments_count": len(segments)
            }
            
        except Exception as e:
            await session.rollback()
            raise


async def _download_segments(segments: List[AnimationSegment]) -> List[str]:
    """
    Скачивает все видео-сегменты во временные файлы.
    
    Returns:
        Список путей к временным файлам
    """
    temp_paths = []
    
    try:
        for segment in segments:
            if not segment.generated_video_url:
                raise ValueError(f"Segment {segment.segment_number} has no video URL")
            
            # Создаем временный файл для каждого сегмента
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f'_segment_{segment.segment_number}.mp4',
                delete=False
            )
            temp_file.close()
            
            # Скачиваем видео из GCS
            await download_file_from_gcs(segment.generated_video_url, temp_file.name)
            temp_paths.append(temp_file.name)
            
            logger.info(f"Downloaded segment {segment.segment_number} to {temp_file.name}")
        
        return temp_paths
        
    except Exception as e:
        # В случае ошибки удаляем уже скачанные файлы
        await _cleanup_temp_files(temp_paths)
        raise


async def _cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Удаляет временные файлы.
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
                logger.debug(f"Cleaned up temp file: {path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {path}: {e}")


async def _update_project_status(project_id: UUID, status: AnimationStatus):
    """
    Обновляет статус проекта.
    """
    async with CeleryAsyncSession() as session:
        try:
            stmt = update(AnimationProject).where(
                AnimationProject.id == project_id
            ).values(status=status)
            
            await session.execute(stmt)
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating project status: {e}")


@celery_app.task(bind=True)
def check_segments_completion_task(self, project_id: str):
    """Checks if all segments are ready and starts assembly when appropriate."""
    try:
        # Shared event loop logic
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(_check_segments_completion_async(UUID(project_id)))
            
    except Exception as exc:
        logger.error(f"Error checking segments completion: {exc}")
        raise


async def _check_segments_completion_async(project_id: UUID) -> dict:
    """
    Проверяет готовность всех сегментов и запускает сборку если нужно.
    """
    async with CeleryAsyncSession() as session:
        try:
            # Получаем проект
            project_query = select(AnimationProject).where(AnimationProject.id == project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Считаем готовые сегменты
            completed_segments_query = select(AnimationSegment).where(
                AnimationSegment.animation_project_id == project_id,
                AnimationSegment.status == AnimationStatus.COMPLETED
            )
            completed_segments_result = await session.execute(completed_segments_query)
            completed_segments = completed_segments_result.scalars().all()
            
            completed_count = len(completed_segments)
            total_count = project.total_segments
            
            logger.info(f"Project {project_id}: {completed_count}/{total_count} segments completed")
            
            if completed_count == total_count:
                # Все сегменты готовы, запускаем сборку
                logger.info(f"All segments ready for project {project_id}, starting assembly")
                assemble_video_task.delay(str(project_id))
                
                return {
                    "status": "assembly_started",
                    "completed_segments": completed_count,
                    "total_segments": total_count
                }
            else:
                return {
                    "status": "waiting",
                    "completed_segments": completed_count,
                    "total_segments": total_count
                }
                
        except Exception as e:
            raise 