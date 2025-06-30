import subprocess
import tempfile
import os
from typing import List
from pathlib import Path


def extract_last_frame(video_path: str, output_image_path: str) -> None:
    """
    Извлекает последний кадр из видео и сохраняет как изображение.
    
    Args:
        video_path: Путь к видеофайлу
        output_image_path: Путь для сохранения изображения
    """
    command = [
        "ffmpeg", "-y",  # Перезаписывать выходной файл
        "-sseof", "-0.1",  # Взять кадр за 0.1 сек до конца
        "-i", video_path,  # Входной файл
        "-update", "1",  # Обновить только один кадр
        "-q:v", "1",  # Максимальное качество
        output_image_path
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg error extracting frame: {e.stderr}")


def concatenate_videos(video_paths: List[str], output_video_path: str) -> None:
    """
    Склеивает список видеофайлов в один.
    
    Args:
        video_paths: Список путей к видеофайлам в порядке склейки
        output_video_path: Путь для сохранения итогового видео
    """
    if not video_paths:
        raise ValueError("Video paths list cannot be empty")
    
    # Создаем временный файл со списком видео
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as filelist:
        for path in video_paths:
            # Экранируем путь для FFmpeg
            escaped_path = path.replace("'", r"\'")
            filelist.write(f"file '{escaped_path}'\n")
        filelist_path = filelist.name
    
    try:
        command = [
            "ffmpeg", "-y",  # Перезаписывать выходной файл
            "-f", "concat",  # Формат concat
            "-safe", "0",  # Разрешить небезопасные пути
            "-i", filelist_path,  # Файл со списком
            "-c", "copy",  # Копировать без перекодирования
            output_video_path
        ]
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg error concatenating videos: {e.stderr}")
    finally:
        # Удаляем временный файл
        os.unlink(filelist_path)


def get_video_duration(video_path: str) -> float:
    """
    Получает длительность видео в секундах.
    
    Args:
        video_path: Путь к видеофайлу
        
    Returns:
        Длительность в секундах
    """
    command = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path
    ]
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Error getting video duration: {e}")


def validate_video_file(video_path: str) -> bool:
    """
    Проверяет, является ли файл валидным видео.
    
    Args:
        video_path: Путь к файлу
        
    Returns:
        True если файл является валидным видео
    """
    if not os.path.exists(video_path):
        return False
    
    command = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        video_path
    ]
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return result.stdout.strip() == "video"
    except subprocess.CalledProcessError:
        return False 