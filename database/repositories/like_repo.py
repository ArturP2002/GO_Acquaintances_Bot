"""
Репозиторий для работы с лайками.
Слой доступа к данным для модели Like.
"""
from typing import Optional
from datetime import datetime, date

from database.models.like import Like
from database.models.user import User


class LikeRepository:
    """Репозиторий для работы с лайками."""
    
    @staticmethod
    def create(from_user_id: int, to_user_id: int) -> Like:
        """
        Создает новый лайк.
        
        Args:
            from_user_id: ID пользователя, который поставил лайк
            to_user_id: ID пользователя, которому поставили лайк
            
        Returns:
            Созданный объект Like
        """
        return Like.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id
        )
    
    @staticmethod
    def exists(from_user_id: int, to_user_id: int) -> bool:
        """
        Проверяет существование лайка.
        
        Args:
            from_user_id: ID пользователя, который поставил лайк
            to_user_id: ID пользователя, которому поставили лайк
            
        Returns:
            True если лайк существует, False в противном случае
        """
        return Like.select().where(
            (Like.from_user_id == from_user_id) &
            (Like.to_user_id == to_user_id)
        ).exists()
    
    @staticmethod
    def get(from_user_id: int, to_user_id: int) -> Optional[Like]:
        """
        Получает лайк между двумя пользователями.
        
        Args:
            from_user_id: ID пользователя, который поставил лайк
            to_user_id: ID пользователя, которому поставили лайк
            
        Returns:
            Like или None если не найден
        """
        try:
            return Like.get(
                (Like.from_user_id == from_user_id) &
                (Like.to_user_id == to_user_id)
            )
        except Like.DoesNotExist:
            return None
    
    @staticmethod
    def count_today_likes(user_id: int) -> int:
        """
        Подсчитывает количество лайков, поставленных пользователем за сегодня.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество лайков за сегодня
        """
        today = date.today()
        return Like.select().where(
            (Like.from_user_id == user_id) &
            (Like.created_at >= datetime.combine(today, datetime.min.time()))
        ).count()
    
    @staticmethod
    def check_reciprocal(from_user_id: int, to_user_id: int) -> bool:
        """
        Проверяет взаимный лайк между двумя пользователями.
        
        Args:
            from_user_id: ID первого пользователя
            to_user_id: ID второго пользователя
            
        Returns:
            True если есть взаимный лайк, False в противном случае
        """
        # Проверяем лайк в обратном направлении
        return Like.select().where(
            (Like.from_user_id == to_user_id) &
            (Like.to_user_id == from_user_id)
        ).exists()
    
    @staticmethod
    def get_liked_users(user_id: int) -> list[User]:
        """
        Получает список пользователей, которым поставил лайк данный пользователь.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список пользователей, которым поставлен лайк
        """
        return [
            like.to_user 
            for like in Like.select().where(Like.from_user_id == user_id)
        ]
    
    @staticmethod
    def get_likes_received(user_id: int) -> list[Like]:
        """
        Получает список лайков, полученных пользователем.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список лайков, полученных пользователем
        """
        return list(Like.select().where(Like.to_user_id == user_id))
    
    @staticmethod
    def count_likes_received(user_id: int) -> int:
        """
        Подсчитывает количество лайков, полученных пользователем.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество полученных лайков
        """
        return Like.select().where(Like.to_user_id == user_id).count()
    
    @staticmethod
    def delete(from_user_id: int, to_user_id: int) -> bool:
        """
        Удаляет лайк.
        
        Args:
            from_user_id: ID пользователя, который поставил лайк
            to_user_id: ID пользователя, которому поставили лайк
            
        Returns:
            True если лайк удален, False если не найден
        """
        try:
            like = Like.get(
                (Like.from_user_id == from_user_id) &
                (Like.to_user_id == to_user_id)
            )
            like.delete_instance()
            return True
        except Like.DoesNotExist:
            return False
