"""
Сервис для работы с профилями пользователей.
Бизнес-логика для создания и управления профилями.
"""
from typing import Optional
from datetime import datetime

from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.settings_repo import SettingsRepository
from core.constants import MIN_AGE_DEFAULT
from config import config


class ProfileService:
    """Сервис для работы с профилями пользователей."""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
    
    def create(self, telegram_id: int, username: Optional[str], name: str, age: int, 
               gender: str, city: Optional[str] = None, bio: Optional[str] = None,
               photo_file_id: Optional[str] = None, video_note_file_id: Optional[str] = None,
               video_note_task: Optional[str] = None, role: str = "user") -> dict:
        """
        Создает профиль пользователя с полной информацией.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Username пользователя (опционально)
            name: Имя пользователя
            age: Возраст
            gender: Пол
            city: Город (опционально)
            bio: Описание профиля (опционально)
            photo_file_id: File ID фото в Telegram (опционально)
            video_note_file_id: File ID кружка в Telegram (опционально)
            video_note_task: Задание для кружка (опционально, если не указано - генерируется случайно)
            role: Роль пользователя (по умолчанию "user", для тестовых анкет - "test")
            
        Returns:
            Словарь с результатом:
            {
                'success': bool,
                'user': User или None,
                'profile': Profile или None,
                'error': str или None
            }
        """
        try:
            # Проверка существования пользователя
            user = self.user_repo.get_by_telegram_id(telegram_id)
            
            if not user:
                # Создание нового пользователя
                user = self.user_repo.create(
                    telegram_id=telegram_id,
                    username=username,
                    is_banned=False,
                    is_verified=False,
                    is_active=True,
                    role=role,
                    last_active=datetime.now()
                )
            
            # Проверка, есть ли уже профиль
            existing_profile = self.profile_repo.get_by_user_id(user.id)
            if existing_profile:
                return {
                    'success': False,
                    'user': user,
                    'profile': existing_profile,
                    'error': 'Профиль уже существует'
                }
            
            # Создание профиля
            profile = self.profile_repo.create(
                user_id=user.id,
                name=name,
                age=age,
                gender=gender,
                city=city,
                bio=bio
            )
            
            # Сохранение медиа (фото и кружок)
            if photo_file_id or video_note_file_id:
                self.profile_repo.add_media(
                    profile_id=profile.id,
                    photo_file_id=photo_file_id,
                    video_note_file_id=video_note_file_id,
                    is_main=True if photo_file_id else False
                )
            
            # Примечание: Создание задачи модерации и отправка в группу 
            # теперь выполняется через ModerationService.create_moderation_task()
            # в обработчике регистрации после создания профиля
            
            return {
                'success': True,
                'user': user,
                'profile': profile,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'user': None,
                'profile': None,
                'error': str(e)
            }
    
    def check_age(self, age: int) -> bool:
        """
        Проверяет возраст пользователя.
        Если возраст < MIN_AGE, пользователь должен быть забанен.
        
        Args:
            age: Возраст пользователя
            
        Returns:
            True если возраст допустим, False если нужно забанить
        """
        min_age = SettingsRepository.get_int("min_age", MIN_AGE_DEFAULT)
        return age >= min_age
