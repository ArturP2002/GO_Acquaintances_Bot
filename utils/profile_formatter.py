"""
Утилиты для форматирования отображения профилей.
Функции для создания текстового представления анкет.
"""
from typing import Optional

from database.models.profile import Profile
from database.repositories.profile_repo import ProfileRepository


def format_profile_text(profile: Profile) -> str:
    """
    Форматирует профиль для отображения в сообщении.
    Создает текстовое представление анкеты с именем, возрастом, городом и описанием.
    
    Args:
        profile: Объект Profile для форматирования
        
    Returns:
        Отформатированная строка с информацией о профиле
    """
    lines = []
    
    # Имя и возраст
    lines.append(f"👤 {profile.name}, {profile.age}")
    
    # Пол
    if profile.gender:
        lines.append(f"⚧️ {profile.gender}")
    
    # Город
    if profile.city:
        lines.append(f"📍 {profile.city}")
    
    # Описание
    if profile.bio:
        lines.append(f"\n📝 {profile.bio}")
    
    return "\n".join(lines)


def get_profile_photo_file_id(profile: Profile) -> Optional[str]:
    """
    Получает file_id главного фото профиля.
    
    Args:
        profile: Объект Profile
        
    Returns:
        file_id фото или None если фото нет
    """
    media = ProfileRepository.get_main_photo(profile.id)
    if media and media.photo_file_id:
        return media.photo_file_id
    return None
