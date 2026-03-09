"""
Репозиторий для работы с пользователями.
Слой доступа к данным для модели User.
"""
from typing import Optional
from datetime import datetime

from database.models.user import User


class UserRepository:
    """Репозиторий для работы с пользователями."""
    
    @staticmethod
    def get_by_telegram_id(telegram_id: int) -> Optional[User]:
        """
        Получает пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            User или None если не найден
        """
        try:
            return User.get(User.telegram_id == telegram_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """
        Получает пользователя по ID.
        
        Args:
            user_id: ID пользователя в БД
            
        Returns:
            User или None если не найден
        """
        try:
            return User.get_by_id(user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def create(telegram_id: int, username: Optional[str] = None, **kwargs) -> User:
        """
        Создает нового пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Username пользователя (опционально)
            **kwargs: Дополнительные поля (is_banned, is_verified, is_active, role, last_active)
            
        Returns:
            Созданный объект User
        """
        return User.create(
            telegram_id=telegram_id,
            username=username,
            **kwargs
        )
    
    @staticmethod
    def update_last_active(user_id: int) -> bool:
        """
        Обновляет время последней активности пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если обновление успешно, False если пользователь не найден
        """
        try:
            user = User.get_by_id(user_id)
            user.last_active = datetime.now()
            user.save()
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def ban_user(user_id: int) -> bool:
        """
        Банит пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        try:
            user = User.get_by_id(user_id)
            user.is_banned = True
            user.save()
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def unban_user(user_id: int) -> bool:
        """
        Разбанивает пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        try:
            user = User.get_by_id(user_id)
            user.is_banned = False
            user.save()
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def verify_user(user_id: int) -> bool:
        """
        Верифицирует пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        try:
            user = User.get_by_id(user_id)
            user.is_verified = True
            user.save()
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def unverify_user(user_id: int) -> bool:
        """
        Снимает верификацию с пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если операция успешна, False если пользователь не найден
        """
        try:
            user = User.get_by_id(user_id)
            user.is_verified = False
            user.save()
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def exists_by_telegram_id(telegram_id: int) -> bool:
        """
        Проверяет существование пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если пользователь существует, False в противном случае
        """
        return User.select().where(User.telegram_id == telegram_id).exists()
    
    @staticmethod
    def get_all_banned() -> list[User]:
        """
        Получает список всех забаненных пользователей.
        
        Returns:
            Список забаненных пользователей
        """
        return list(User.select().where(User.is_banned == True))
    
    @staticmethod
    def get_all_verified() -> list[User]:
        """
        Получает список всех верифицированных пользователей.
        
        Returns:
            Список верифицированных пользователей
        """
        return list(User.select().where(User.is_verified == True))
