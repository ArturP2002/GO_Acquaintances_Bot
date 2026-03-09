"""
Утилиты для работы с медиа-файлами.
Функции для обработки фото и видео-кружков.
"""
from typing import Optional
from aiogram.types import PhotoSize, VideoNote


def get_largest_photo(photos: list[PhotoSize]) -> Optional[PhotoSize]:
    """
    Получает фото с наибольшим размером из списка.
    
    Args:
        photos: Список объектов PhotoSize
        
    Returns:
        PhotoSize с наибольшим размером или None если список пуст
    """
    if not photos:
        return None
    
    return max(photos, key=lambda p: p.width * p.height)


def validate_photo_size(photo: PhotoSize, min_size: int = 200) -> bool:
    """
    Проверяет, что фото имеет достаточный размер.
    
    Args:
        photo: Объект PhotoSize
        min_size: Минимальный размер (ширина или высота)
        
    Returns:
        True если фото подходит, False иначе
    """
    if not photo:
        return False
    
    return photo.width >= min_size or photo.height >= min_size


def validate_video_note(video_note: VideoNote) -> bool:
    """
    Проверяет, что видео-кружок валиден.
    
    Args:
        video_note: Объект VideoNote
        
    Returns:
        True если кружок валиден, False иначе
    """
    if not video_note:
        return False
    
    # Проверяем, что есть file_id
    if not video_note.file_id:
        return False
    
    # Проверяем длительность (кружок должен быть не слишком коротким)
    if video_note.duration and video_note.duration < 1:
        return False
    
    return True


def format_file_size(size_bytes: int) -> str:
    """
    Форматирует размер файла в читаемый вид.
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированная строка (например, "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
