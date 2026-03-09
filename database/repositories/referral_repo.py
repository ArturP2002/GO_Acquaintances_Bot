"""
Репозиторий для работы с реферальной системой.
Слой доступа к данным для модели Referral.
"""
from typing import Optional, List
from datetime import datetime

from database.models.referral import Referral
from database.models.user import User


class ReferralRepository:
    """Репозиторий для работы с рефералами."""
    
    @staticmethod
    def create(inviter_id: int, invited_id: int) -> Referral:
        """
        Создает новую реферальную связь.
        
        Args:
            inviter_id: ID пользователя, который пригласил
            invited_id: ID приглашенного пользователя
            
        Returns:
            Созданный объект Referral
            
        Raises:
            ValueError: Если inviter_id == invited_id (нельзя пригласить себя)
            Exception: Если связь уже существует (unique constraint)
        """
        if inviter_id == invited_id:
            raise ValueError("Пользователь не может пригласить себя")
        
        try:
            referral = Referral.create(
                inviter_id=inviter_id,
                invited_id=invited_id,
                reward_given=False
            )
            return referral
        except Exception as e:
            # Если связь уже существует, возвращаем существующую
            try:
                return Referral.get(
                    (Referral.inviter_id == inviter_id) &
                    (Referral.invited_id == invited_id)
                )
            except Referral.DoesNotExist:
                raise e
    
    @staticmethod
    def get_by_invited(invited_id: int) -> Optional[Referral]:
        """
        Получает реферальную связь по ID приглашенного пользователя.
        
        Args:
            invited_id: ID приглашенного пользователя
            
        Returns:
            Referral или None если не найдена
        """
        try:
            return Referral.get(Referral.invited_id == invited_id)
        except Referral.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_inviter(inviter_id: int) -> List[Referral]:
        """
        Получает список всех реферальных связей для пользователя, который пригласил.
        
        Args:
            inviter_id: ID пользователя, который пригласил
            
        Returns:
            Список объектов Referral
        """
        return list(Referral.select().where(Referral.inviter_id == inviter_id))
    
    @staticmethod
    def count_by_inviter(inviter_id: int) -> int:
        """
        Подсчитывает количество приглашенных пользователей.
        
        Args:
            inviter_id: ID пользователя, который пригласил
            
        Returns:
            Количество приглашенных пользователей
        """
        return Referral.select().where(Referral.inviter_id == inviter_id).count()
    
    @staticmethod
    def mark_reward_given(referral_id: int) -> bool:
        """
        Отмечает, что награда за реферала выдана.
        
        Args:
            referral_id: ID реферальной связи
            
        Returns:
            True если обновлено успешно, False если не найдено
        """
        try:
            referral = Referral.get_by_id(referral_id)
            referral.reward_given = True
            referral.save()
            return True
        except Referral.DoesNotExist:
            return False
    
    @staticmethod
    def is_reward_given(inviter_id: int, invited_id: int) -> bool:
        """
        Проверяет, выдана ли награда за конкретную реферальную связь.
        
        Args:
            inviter_id: ID пользователя, который пригласил
            invited_id: ID приглашенного пользователя
            
        Returns:
            True если награда выдана, False в противном случае
        """
        try:
            referral = Referral.get(
                (Referral.inviter_id == inviter_id) &
                (Referral.invited_id == invited_id)
            )
            return referral.reward_given
        except Referral.DoesNotExist:
            return False
    
    @staticmethod
    def exists(inviter_id: int, invited_id: int) -> bool:
        """
        Проверяет существование реферальной связи.
        
        Args:
            inviter_id: ID пользователя, который пригласил
            invited_id: ID приглашенного пользователя
            
        Returns:
            True если связь существует, False в противном случае
        """
        return Referral.select().where(
            (Referral.inviter_id == inviter_id) &
            (Referral.invited_id == invited_id)
        ).exists()
    
    @staticmethod
    def get_pending_rewards(inviter_id: int) -> List[Referral]:
        """
        Получает список реферальных связей с невыданными наградами.
        
        Args:
            inviter_id: ID пользователя, который пригласил
            
        Returns:
            Список объектов Referral с reward_given=False
        """
        return list(Referral.select().where(
            (Referral.inviter_id == inviter_id) &
            (Referral.reward_given == False)
        ))
