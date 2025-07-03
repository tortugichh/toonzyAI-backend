#!/usr/bin/env python3
"""
Задачи для генерации видео анимации
"""
import asyncio
import tempfile
import os
from uuid import UUID
from typing import Optional
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
import logging

from utils.celery_app import celery_app
from utils.vertex_ai_client_v2 import generate_video_from_image_v2  # Veo 2.0 с long-running operations
from utils.ffmpeg_utils import extract_last_frame
from utils.gcs_client import upload_file_to_gcs, download_file_from_gcs
from db.avatar_repository import (
    AnimationProject, 
    AnimationSegment, 
    AnimationStatus,
    Avatar
)

logger = logging.getLogger(__name__)

# Создаем отдельный движок для Celery задач
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")

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


@celery_app.task(name="tasks.generation_tasks.generate_segment_task", bind=True, max_retries=3)
def generate_segment_task(self, project_id: str, segment_number: int):
    """
    ИСПРАВЛЕННАЯ Celery задача для генерации сегмента видео.
    Использует правильное управление event loop для Celery.
    
    Args:
        project_id: UUID проекта анимации
        segment_number: Номер сегмента для генерации
        
    Returns:
        dict: Результат генерации
    """
    try:
        logger.info(f"🎬 Starting segment generation task: project {project_id}, segment {segment_number}")
        
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
        
        logger.info(f"✅ Segment generation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in generate_segment_task: {e}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying... attempt {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(countdown=60 * (self.request.retries + 1))  # Увеличиваем интервал
        else:
            logger.error(f"❌ Max retries reached for project {project_id}, segment {segment_number}")
            raise


async def _generate_segment_async(project_id: UUID, segment_number: int) -> dict:
    """
    Асинхронная функция для генерации сегмента.
    """
    async with CeleryAsyncSession() as session:
        try:
            # 1. Получаем информацию о проекте
            project_query = select(AnimationProject).where(AnimationProject.id == project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Animation project {project_id} not found")
            
            # 2. Получаем сегмент для обработки
            segment_query = select(AnimationSegment).where(
                AnimationSegment.animation_project_id == project_id,
                AnimationSegment.segment_number == segment_number
            )
            segment_result = await session.execute(segment_query)
            segment = segment_result.scalar_one_or_none()
            
            if not segment:
                raise ValueError(f"Segment {segment_number} not found")
            
            # 3. Обновляем статус на IN_PROGRESS
            segment.status = AnimationStatus.IN_PROGRESS
            segment.progress = 10
            await session.commit()
            
            logger.info(f"Starting generation for project {project_id}, segment {segment_number}")
            
            # 4. Определяем исходное изображение
            start_frame_url = await _get_start_frame_url(session, project, segment, segment_number)
            
            # 5. Определяем промпт для генерации - промпт ОБЯЗАТЕЛЕН для каждого сегмента
            if not segment.segment_prompt:
                raise ValueError("Segment prompt is required before generation")
            generation_prompt = segment.segment_prompt
            logger.info(f"🎯 Using prompt for segment {segment_number}: '{generation_prompt[:50]}...'")
            
            # 6. Генерируем видео используя Veo 2.0 (БЕЗ FALLBACK!)
            logger.info("Generating video with Veo 2.0 - NO FALLBACKS!")
            generated_video_url = await generate_video_from_image_v2(
                start_frame_url=start_frame_url,
                animation_prompt=generation_prompt,  # ИСПОЛЬЗУЕМ ИНДИВИДУАЛЬНЫЙ ПРОМПТ!
                duration_seconds=5  # Veo 2.0 поддерживает только 5, 6, 7, 8 секунд
            )
            
            # 7. Обновляем сегмент с результатом
            segment.generated_video_url = generated_video_url
            segment.status = AnimationStatus.COMPLETED
            segment.progress = 90
            await session.commit()
            
            logger.info(f"✅ Completed generation for segment {segment_number}: {generated_video_url}")
            logger.info(f"🎬 Used prompt: '{generation_prompt}'")
            
            # 8. НЕ ЗАПУСКАЕМ АВТОМАТИЧЕСКИ СЛЕДУЮЩИЙ СЕГМЕНТ!
            # Пользователь сам решает когда генерировать каждый сегмент!
            logger.info(f"🎯 Segment {segment_number} completed. User controls next steps!")
            
            segment.progress = 100
            await session.commit()
            
            return {
                "status": "completed",
                "segment_number": segment_number,
                "video_url": generated_video_url
            }
            
        except Exception as e:
            await session.rollback()
            raise


async def _get_start_frame_url(session: AsyncSession, project: AnimationProject, segment: AnimationSegment, segment_number: int) -> str:
    """
    Определяет URL исходного кадра для генерации сегмента.
    
    ДЛЯ ПАРАЛЛЕЛЬНОЙ ГЕНЕРАЦИИ: Все сегменты используют исходный аватар как стартовый кадр.
    Это позволяет генерировать все сегменты независимо и параллельно.
    """
    # Получаем исходный аватар (для всех сегментов)
    avatar_query = select(Avatar).where(Avatar.id == project.source_avatar_id)
    avatar_result = await session.execute(avatar_query)
    avatar = avatar_result.scalar_one_or_none()
    
    if not avatar:
        raise ValueError(f"Source avatar {project.source_avatar_id} not found")
    
    # Создаем временный файл изображения из бинарных данных
    if avatar.image_data:
        # Создаем временный файл из binary data аватара
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_avatar:
            temp_avatar.write(avatar.image_data)
            temp_avatar_path = temp_avatar.name
        
        # Загружаем аватар в GCS для доступа через URL
        avatar_url = await upload_file_to_gcs(
            temp_avatar_path,
            f"avatars/{avatar.id}_segment_{segment_number}.jpg"  # Уникальное имя для каждого сегмента
        )
        
        # Удаляем временный файл
        os.unlink(temp_avatar_path)
        
        # Обновляем прогресс текущего сегмента
        segment.progress = 30
        await session.commit()
        
        logger.info(f"🎯 Segment {segment_number}: Using avatar as start frame for parallel generation")
        return avatar_url
    else:
        raise ValueError(f"Avatar {avatar.id} has no image data")


async def _extract_last_frame_from_video(session: AsyncSession, segment: AnimationSegment, video_url: str) -> str:
    """
    Извлекает последний кадр из видео и возвращает URL на него.
    """
    with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_video:
        with tempfile.NamedTemporaryFile(suffix='.jpg') as temp_frame:
            
            # Скачиваем видео из GCS
            await download_file_from_gcs(video_url, temp_video.name)
            
            # Извлекаем последний кадр
            extract_last_frame(temp_video.name, temp_frame.name)
            
            # Загружаем кадр обратно в GCS
            frame_url = await upload_file_to_gcs(
                temp_frame.name,
                f"animations/frames/{os.path.basename(temp_frame.name)}"
            )
            
            # Обновляем прогресс после получения кадра
            segment.progress = 90
            await session.commit()
            
            return frame_url


async def _update_segment_status(project_id: UUID, segment_number: int, status: AnimationStatus):
    """
    Обновляет статус сегмента.
    """
    async with CeleryAsyncSession() as session:
        try:
            stmt = update(AnimationSegment).where(
                AnimationSegment.animation_project_id == project_id,
                AnimationSegment.segment_number == segment_number
            ).values(status=status)
            
            await session.execute(stmt)
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating segment status: {e}")


@celery_app.task(bind=True)
def create_animation_segments_task(self, project_id: str):
    """
    Задача для создания записей сегментов в БД после создания проекта.
    """
    try:
        # Создаем новый event loop для Celery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _create_segments_async(UUID(project_id))
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Error creating segments: {exc}")
        raise


async def _create_segments_async(project_id: UUID) -> dict:
    """
    Создает записи сегментов в БД и запускает генерацию первого.
    """
    async with CeleryAsyncSession() as session:
        try:
            # Получаем проект
            project_query = select(AnimationProject).where(AnimationProject.id == project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Проверяем, не созданы ли уже сегменты
            existing_segments_query = select(AnimationSegment).where(
                AnimationSegment.animation_project_id == project_id
            )
            existing_segments_result = await session.execute(existing_segments_query)
            existing_segments = existing_segments_result.scalars().all()
            
            if len(existing_segments) > 0:
                logger.info(f"Segments already exist for project {project_id}, skipping creation")
                return {"status": "segments_already_exist", "total_segments": len(existing_segments)}
            
            # Создаем записи для всех сегментов - БЕЗ АВТОЗАПУСКА!
            for i in range(1, project.total_segments + 1):
                segment = AnimationSegment(
                    animation_project_id=project_id,
                    segment_number=i,
                    status=AnimationStatus.PENDING,
                    start_frame_url="",  # Будет заполнено при генерации
                    segment_prompt=None  # Пользователь может задать индивидуальный промпт
                )
                session.add(segment)
            
            await session.commit()
            
            # НЕ ЗАПУСКАЕМ АВТОМАТИЧЕСКИ! Пользователь сам контролирует каждый сегмент!
            logger.info(f"🎯 Created {project.total_segments} segments for project {project_id}")
            logger.info(f"🎮 User can now control each segment individually!")
            
            return {
                "status": "segments_created", 
                "total_segments": project.total_segments,
                "message": "Segments created. User can now generate each segment individually."
            }
            
        except Exception as e:
            await session.rollback()
            raise 