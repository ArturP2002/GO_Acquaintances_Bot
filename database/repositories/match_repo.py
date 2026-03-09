"""
Репозиторий для работы с мэтчами.
Слой доступа к данным для модели Match.
"""
from typing import Optional, List

from database.models.match import Match
from database.models.user import User


class MatchRepository:
    """Репозиторий для работы с мэтчами."""
    
    @staticmethod
    def create(user1_id: int, user2_id: int) -> Match:
        """
        Создает новый мэтч между двумя пользователями.
        Упорядочивает ID пользователей для консистентности (меньший ID всегда user1).
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            
        Returns:
            Созданный объект Match
        """
        # Упорядочиваем ID для консистентности
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        return Match.create(
            user1_id=user1_id,
            user2_id=user2_id
        )
    
    @staticmethod
    def exists(user1_id: int, user2_id: int) -> bool:
        """
        Проверяет существование мэтча между двумя пользователями.
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            
        Returns:
            True если мэтч существует, False в противном случае
        """
        # Упорядочиваем ID для проверки
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        return Match.select().where(
            (Match.user1_id == user1_id) &
            (Match.user2_id == user2_id)
        ).exists()
    
    @staticmethod
    def get(user1_id: int, user2_id: int) -> Optional[Match]:
        """
        Получает мэтч между двумя пользователями.
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            
        Returns:
            Match или None если не найден
        """
        # Упорядочиваем ID для поиска
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        try:
            return Match.get(
                (Match.user1_id == user1_id) &
                (Match.user2_id == user2_id)
            )
        except Match.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_matches(user_id: int) -> List[Match]:
        """
        Получает список всех мэтчей пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список мэтчей пользователя
        """
        return list(
            Match.select().where(
                (Match.user1_id == user_id) | (Match.user2_id == user_id)
            )
        )
    
    @staticmethod
    def get_match_partners(user_id: int) -> List[User]:
        """
        Получает список пользователей, с которыми у данного пользователя есть мэтч.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список пользователей-партнеров по мэтчам
        """
        matches = MatchRepository.get_user_matches(user_id)
        partners = []
        
        for match in matches:
            if match.user1_id == user_id:
                partners.append(match.user2)
            else:
                partners.append(match.user1)
        
        return partners
    
    @staticmethod
    def count_user_matches(user_id: int) -> int:
        """
        Подсчитывает количество мэтчей пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество мэтчей
        """
        return Match.select().where(
            (Match.user1_id == user_id) | (Match.user2_id == user_id)
        ).count()
    
    @staticmethod
    def get_recent_matches(user_id: int, since_datetime) -> List[Match]:
        """
        Получает список мэтчей пользователя, созданных после указанной даты.
        
        Args:
            user_id: ID пользователя
            since_datetime: Дата, после которой искать мэтчи
            
        Returns:
            Список недавних мэтчей
        """
        return list(
            Match.select().where(
                ((Match.user1_id == user_id) | (Match.user2_id == user_id)) &
                (Match.created_at >= since_datetime)
            )
        )
    
    @staticmethod
    def delete(user1_id: int, user2_id: int) -> bool:
        """
        Удаляет мэтч между двумя пользователями.
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            
        Returns:
            True если мэтч удален, False если не найден
        """
        # Упорядочиваем ID для поиска
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        try:
            match = Match.get(
                (Match.user1_id == user1_id) &
                (Match.user2_id == user2_id)
            )
            match.delete_instance()
            return True
        except Match.DoesNotExist:
            return False
