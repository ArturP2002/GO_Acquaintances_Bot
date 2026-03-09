"""
Сервис для работы с пользователями.
Бизнес-логика для управления пользователями.
"""
from typing import Optional
from datetime import datetime

from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository


class UserService:
    """Сервис для работы с пользователями."""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
    
    def get_or_create_user(self, telegram_id: int, username: Optional[str] = None) -> tuple[bool, any]:
        """
        Получает пользователя или создает нового, если не существует.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Username пользователя (опционально)
            
        Returns:
            Кортеж (is_new, user):
            - is_new: True если пользователь был создан, False если уже существовал
            - user: Объект User
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        
        if user:
            # Обновляем username если изменился
            if username and user.username != username:
                user.username = username
                user.save()
            return False, user
        
        # Создаем нового пользователя
        user = self.user_repo.create(
            telegram_id=telegram_id,
            username=username,
            is_banned=False,
            is_verified=False,
            is_active=True,
            role='user',
            last_active=datetime.now()
        )
        
        return True, user
    
    def update_last_active(self, telegram_id: int) -> bool:
        """
        Обновляет время последней активности пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если обновление успешно, False если пользователь не найден
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        return self.user_repo.update_last_active(user.id)
    
    def is_user_registered(self, telegram_id: int) -> bool:
        """
        Проверяет, зарегистрирован ли пользователь (есть ли у него профиль).
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если пользователь зарегистрирован, False иначе
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        profile = self.profile_repo.get_by_user_id(user.id)
        return profile is not None
    
    def is_user_verified(self, telegram_id: int) -> bool:
        """
        Проверяет, верифицирован ли пользователь.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если пользователь верифицирован, False иначе
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        return user.is_verified
    
    def is_user_banned(self, telegram_id: int) -> bool:
        """
        Проверяет, забанен ли пользователь.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если пользователь забанен, False иначе
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        return user.is_banned
    
    def ban_user(self, telegram_id: int) -> bool:
        """
        Банит пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        return self.user_repo.ban_user(user.id)
    
    def unban_user(self, telegram_id: int) -> bool:
        """
        Разбанивает пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        return self.user_repo.unban_user(user.id)
    
    def verify_user(self, telegram_id: int) -> bool:
        """
        Верифицирует пользователя (одобряет модерацию).
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        return self.user_repo.verify_user(user.id)
    
    def get_user_info(self, telegram_id: int) -> Optional[dict]:
        """
        Получает полную информацию о пользователе.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Словарь с информацией о пользователе или None если не найден
        """
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        profile = self.profile_repo.get_by_user_id(user.id)
        
        return {
            'user': user,
            'profile': profile,
            'is_registered': profile is not None,
            'is_verified': user.is_verified,
            'is_banned': user.is_banned,
            'is_active': user.is_active
        }
