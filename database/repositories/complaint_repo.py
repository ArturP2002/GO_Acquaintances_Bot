"""
Репозиторий для работы с жалобами.
Слой доступа к данным для моделей Complaint и ComplaintAction.
"""
from typing import Optional, List
from datetime import datetime

from database.models.complaint import Complaint, ComplaintAction
from database.models.user import User
from core.constants import ComplaintStatus, ComplaintReason


class ComplaintRepository:
    """Репозиторий для работы с жалобами."""
    
    @staticmethod
    def create(reporter_id: int, reported_id: int, reason: str, 
               description: Optional[str] = None) -> Complaint:
        """
        Создает новую жалобу.
        
        Args:
            reporter_id: ID пользователя, который подал жалобу
            reported_id: ID пользователя, на которого пожаловались
            reason: Причина жалобы (из ComplaintReason)
            description: Описание жалобы (опционально)
            
        Returns:
            Созданный объект Complaint
        """
        return Complaint.create(
            reporter_id=reporter_id,
            reported_id=reported_id,
            reason=reason,
            description=description,
            status=ComplaintStatus.PENDING
        )
    
    @staticmethod
    def get_by_id(complaint_id: int) -> Optional[Complaint]:
        """
        Получает жалобу по ID.
        
        Args:
            complaint_id: ID жалобы
            
        Returns:
            Complaint или None если не найдена
        """
        try:
            return Complaint.get_by_id(complaint_id)
        except Complaint.DoesNotExist:
            return None
    
    @staticmethod
    def get_pending() -> List[Complaint]:
        """
        Получает список всех ожидающих обработки жалоб.
        
        Returns:
            Список жалоб со статусом PENDING
        """
        return list(
            Complaint.select().where(Complaint.status == ComplaintStatus.PENDING)
        )
    
    @staticmethod
    def get_by_status(status: str) -> List[Complaint]:
        """
        Получает список жалоб по статусу.
        
        Args:
            status: Статус жалобы (из ComplaintStatus)
            
        Returns:
            Список жалоб с указанным статусом
        """
        return list(Complaint.select().where(Complaint.status == status))
    
    @staticmethod
    def get_by_reported_user(reported_id: int) -> List[Complaint]:
        """
        Получает список жалоб на конкретного пользователя.
        
        Args:
            reported_id: ID пользователя, на которого пожаловались
            
        Returns:
            Список жалоб на пользователя
        """
        return list(
            Complaint.select().where(Complaint.reported_id == reported_id)
        )
    
    @staticmethod
    def update_status(complaint_id: int, status: str) -> bool:
        """
        Обновляет статус жалобы.
        
        Args:
            complaint_id: ID жалобы
            status: Новый статус (из ComplaintStatus)
            
        Returns:
            True если обновление успешно, False если жалоба не найдена
        """
        try:
            complaint = Complaint.get_by_id(complaint_id)
            complaint.status = status
            complaint.save()
            return True
        except Complaint.DoesNotExist:
            return False
    
    @staticmethod
    def add_action(complaint_id: int, moderator_id: int, action: str, 
                   comment: Optional[str] = None) -> ComplaintAction:
        """
        Добавляет действие модератора по жалобе.
        
        Args:
            complaint_id: ID жалобы
            moderator_id: ID модератора
            action: Действие (ban, unban, dismiss, etc.)
            comment: Комментарий модератора (опционально)
            
        Returns:
            Созданный объект ComplaintAction
        """
        return ComplaintAction.create(
            complaint_id=complaint_id,
            moderator_id=moderator_id,
            action=action,
            comment=comment
        )
    
    @staticmethod
    def get_actions(complaint_id: int) -> List[ComplaintAction]:
        """
        Получает список всех действий по жалобе.
        
        Args:
            complaint_id: ID жалобы
            
        Returns:
            Список действий по жалобе
        """
        return list(
            ComplaintAction.select().where(
                ComplaintAction.complaint_id == complaint_id
            ).order_by(ComplaintAction.created_at)
        )
    
    @staticmethod
    def exists(reporter_id: int, reported_id: int) -> bool:
        """
        Проверяет существование жалобы от одного пользователя на другого.
        
        Args:
            reporter_id: ID пользователя, который подал жалобу
            reported_id: ID пользователя, на которого пожаловались
            
        Returns:
            True если жалоба существует, False в противном случае
        """
        return Complaint.select().where(
            (Complaint.reporter_id == reporter_id) &
            (Complaint.reported_id == reported_id)
        ).exists()
    
    @staticmethod
    def count_by_reported_user(reported_id: int) -> int:
        """
        Подсчитывает количество жалоб на пользователя.
        
        Args:
            reported_id: ID пользователя
            
        Returns:
            Количество жалоб
        """
        return Complaint.select().where(
            Complaint.reported_id == reported_id
        ).count()
