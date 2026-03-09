"""
Репозиторий для работы с модерацией.
Слой доступа к данным для моделей ModerationQueue и ModerationAction.
"""
from typing import Optional, List
from datetime import datetime

from database.models.moderation import ModerationQueue, ModerationAction
from database.models.user import User
from database.models.profile import Profile
from core.constants import ModerationStatus


class ModerationRepository:
    """Репозиторий для работы с модерацией."""
    
    @staticmethod
    def create(user_id: int, profile_id: int, task: str) -> ModerationQueue:
        """
        Создает новую задачу модерации.
        
        Args:
            user_id: ID пользователя
            profile_id: ID профиля на модерации
            task: Задание для кружка (например, 'Покажи 👍')
            
        Returns:
            Созданный объект ModerationQueue
        """
        return ModerationQueue.create(
            user_id=user_id,
            profile_id=profile_id,
            task=task,
            status=ModerationStatus.PENDING
        )
    
    @staticmethod
    def get_by_id(moderation_id: int) -> Optional[ModerationQueue]:
        """
        Получает задачу модерации по ID.
        
        Args:
            moderation_id: ID задачи модерации
            
        Returns:
            ModerationQueue или None если не найдена
        """
        try:
            return ModerationQueue.get_by_id(moderation_id)
        except ModerationQueue.DoesNotExist:
            return None
    
    @staticmethod
    def get_pending() -> List[ModerationQueue]:
        """
        Получает список всех ожидающих обработки задач модерации.
        
        Returns:
            Список задач со статусом PENDING
        """
        return list(
            ModerationQueue.select().where(
                ModerationQueue.status == ModerationStatus.PENDING
            ).order_by(ModerationQueue.created_at)
        )
    
    @staticmethod
    def get_by_status(status: str) -> List[ModerationQueue]:
        """
        Получает список задач модерации по статусу.
        
        Args:
            status: Статус модерации (из ModerationStatus)
            
        Returns:
            Список задач с указанным статусом
        """
        return list(
            ModerationQueue.select().where(
                ModerationQueue.status == status
            ).order_by(ModerationQueue.created_at)
        )
    
    @staticmethod
    def get_by_user(user_id: int) -> List[ModerationQueue]:
        """
        Получает список задач модерации для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список задач модерации пользователя
        """
        return list(
            ModerationQueue.select().where(
                ModerationQueue.user_id == user_id
            ).order_by(ModerationQueue.created_at)
        )
    
    @staticmethod
    def get_by_profile(profile_id: int) -> List[ModerationQueue]:
        """
        Получает список задач модерации для профиля.
        
        Args:
            profile_id: ID профиля
            
        Returns:
            Список задач модерации профиля
        """
        return list(
            ModerationQueue.select().where(
                ModerationQueue.profile_id == profile_id
            ).order_by(ModerationQueue.created_at)
        )
    
    @staticmethod
    def update_status(moderation_id: int, status: str) -> bool:
        """
        Обновляет статус задачи модерации.
        
        Args:
            moderation_id: ID задачи модерации
            status: Новый статус (из ModerationStatus)
            
        Returns:
            True если обновление успешно, False если задача не найдена
        """
        try:
            moderation = ModerationQueue.get_by_id(moderation_id)
            moderation.status = status
            moderation.moderated_at = datetime.now()
            moderation.save()
            return True
        except ModerationQueue.DoesNotExist:
            return False
    
    @staticmethod
    def add_action(moderation_id: int, moderator_id: int, action: str,
                   comment: Optional[str] = None) -> ModerationAction:
        """
        Добавляет действие модератора по задаче модерации.
        
        Args:
            moderation_id: ID задачи модерации
            moderator_id: ID модератора
            action: Действие (approve, reject, ban, etc.)
            comment: Комментарий модератора (опционально)
            
        Returns:
            Созданный объект ModerationAction
        """
        return ModerationAction.create(
            moderation_id=moderation_id,
            moderator_id=moderator_id,
            action=action,
            comment=comment
        )
    
    @staticmethod
    def get_actions(moderation_id: int) -> List[ModerationAction]:
        """
        Получает список всех действий по задаче модерации.
        
        Args:
            moderation_id: ID задачи модерации
            
        Returns:
            Список действий по задаче модерации
        """
        return list(
            ModerationAction.select().where(
                ModerationAction.moderation_id == moderation_id
            ).order_by(ModerationAction.created_at)
        )
    
    @staticmethod
    def get_pending_for_profile(profile_id: int) -> Optional[ModerationQueue]:
        """
        Получает ожидающую задачу модерации для профиля.
        
        Args:
            profile_id: ID профиля
            
        Returns:
            ModerationQueue или None если не найдена
        """
        try:
            return ModerationQueue.get(
                (ModerationQueue.profile_id == profile_id) &
                (ModerationQueue.status == ModerationStatus.PENDING)
            )
        except ModerationQueue.DoesNotExist:
            return None
    
    @staticmethod
    def count_pending() -> int:
        """
        Подсчитывает количество ожидающих задач модерации.
        
        Returns:
            Количество задач со статусом PENDING
        """
        return ModerationQueue.select().where(
            ModerationQueue.status == ModerationStatus.PENDING
        ).count()
