"""
Репозиторий для работы с бустами.
Слой доступа к данным для модели Boost.
"""
from typing import List, Optional
from datetime import datetime

from database.models.boost import Boost
from database.models.user import User


class BoostRepository:
    """Репозиторий для работы с бустами."""
    
    @staticmethod
    def create(user_id: int, boost_value: int, expires_at: Optional[datetime] = None) -> Boost:
        """
        Создает новый буст для пользователя.
        
        Args:
            user_id: ID пользователя
            boost_value: Значение буста (0=обычный, 1=реферальный, 3=платный)
            expires_at: Дата и время истечения буста (опционально)
            
        Returns:
            Созданный объект Boost
        """
        return Boost.create(
            user_id=user_id,
            boost_value=boost_value,
            expires_at=expires_at
        )
    
    @staticmethod
    def get_by_id(boost_id: int) -> Optional[Boost]:
        """
        Получает буст по ID.
        
        Args:
            boost_id: ID буста
            
        Returns:
            Boost или None если не найден
        """
        try:
            return Boost.get_by_id(boost_id)
        except Boost.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_boosts(user_id: int) -> List[Boost]:
        """
        Получает список активных бустов пользователя.
        Активными считаются бусты, у которых expires_at > NOW() или expires_at = NULL.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список активных бустов
        """
        now = datetime.now()
        return list(
            Boost.select().where(
                (Boost.user_id == user_id) &
                (
                    (Boost.expires_at.is_null()) |
                    (Boost.expires_at > now)
                )
            )
        )
    
    @staticmethod
    def get_total_boost_value(user_id: int) -> int:
        """
        Вычисляет суммарное значение активных бустов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Суммарное значение активных бустов
        """
        active_boosts = BoostRepository.get_active_boosts(user_id)
        return sum(boost.boost_value for boost in active_boosts)
    
    @staticmethod
    def get_all_boosts(user_id: int) -> List[Boost]:
        """
        Получает список всех бустов пользователя (включая истекшие).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список всех бустов пользователя
        """
        return list(
            Boost.select().where(Boost.user_id == user_id).order_by(
                Boost.created_at.desc()
            )
        )
    
    @staticmethod
    def get_expired_boosts(user_id: int) -> List[Boost]:
        """
        Получает список истекших бустов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список истекших бустов
        """
        now = datetime.now()
        return list(
            Boost.select().where(
                (Boost.user_id == user_id) &
                (Boost.expires_at.is_null(False)) &
                (Boost.expires_at <= now)
            )
        )
    
    @staticmethod
    def delete_expired() -> int:
        """
        Удаляет все истекшие бусты из базы данных.
        
        Returns:
            Количество удаленных бустов
        """
        now = datetime.now()
        query = Boost.delete().where(
            (Boost.expires_at.is_null(False)) &
            (Boost.expires_at <= now)
        )
        return query.execute()
    
    @staticmethod
    def delete(boost_id: int) -> bool:
        """
        Удаляет буст.
        
        Args:
            boost_id: ID буста
            
        Returns:
            True если буст удален, False если не найден
        """
        try:
            boost = Boost.get_by_id(boost_id)
            boost.delete_instance()
            return True
        except Boost.DoesNotExist:
            return False
    
    @staticmethod
    def count_active_boosts(user_id: int) -> int:
        """
        Подсчитывает количество активных бустов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество активных бустов
        """
        return len(BoostRepository.get_active_boosts(user_id))
