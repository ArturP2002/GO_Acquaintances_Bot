"""
API endpoints для управления жалобами.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from admin_panel.mini_app.backend.dependencies import get_current_admin, require_moderator
from admin_panel.mini_app.backend.schemas import (
    ComplaintResponse, ComplaintUpdate, ComplaintListResponse
)
from database.models.user import User
from database.repositories.complaint_repo import ComplaintRepository
from database.repositories.user_repo import UserRepository
from core.constants import ComplaintStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=ComplaintListResponse)
async def get_complaints(
    status_filter: Optional[str] = Query(None, alias="status", description="Фильтр по статусу"),
    reported_id: Optional[int] = Query(None, description="Фильтр по ID пользователя, на которого пожаловались"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    admin: User = Depends(get_current_admin)
):
    """
    Получение списка жалоб с фильтрацией и пагинацией.
    
    Доступ: все администраторы
    """
    try:
        from database.models.complaint import Complaint
        
        # Построение запроса
        query = Complaint.select()
        
        if status_filter:
            query = query.where(Complaint.status == status_filter)
        if reported_id:
            query = query.where(Complaint.reported_id == reported_id)
        
        # Сортировка по дате создания (новые сначала)
        query = query.order_by(Complaint.created_at.desc())
        
        # Подсчет общего количества
        total = query.count()
        
        # Пагинация
        offset = (page - 1) * page_size
        complaints = list(query.offset(offset).limit(page_size))
        
        return ComplaintListResponse(
            complaints=[ComplaintResponse.model_validate(c) for c in complaints],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка жалоб: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка жалоб"
        )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    admin: User = Depends(get_current_admin)
):
    """
    Получение информации о жалобе по ID.
    
    Доступ: все администраторы
    """
    complaint = ComplaintRepository.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Жалоба не найдена"
        )
    
    return ComplaintResponse.model_validate(complaint)


@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: int,
    complaint_update: ComplaintUpdate,
    admin: User = Depends(require_moderator)
):
    """
    Обновление статуса жалобы и добавление действия модератора.
    
    Доступ: moderator и выше
    """
    complaint = ComplaintRepository.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Жалоба не найдена"
        )
    
    # Обновление статуса
    ComplaintRepository.update_status(complaint_id, complaint_update.status)
    
    # Добавление действия модератора
    ComplaintRepository.add_action(
        complaint_id=complaint_id,
        moderator_id=admin.id,
        action=complaint_update.status,
        comment=complaint_update.comment
    )
    
    # Обновление жалобы
    complaint = ComplaintRepository.get_by_id(complaint_id)
    
    logger.info(
        f"Администратор {admin.id} обновил жалобу {complaint_id}: "
        f"статус={complaint_update.status}"
    )
    
    return ComplaintResponse.model_validate(complaint)


@router.post("/{complaint_id}/ban-reported")
async def ban_reported_user(
    complaint_id: int,
    admin: User = Depends(require_moderator)
):
    """
    Бан пользователя, на которого пожаловались, и обновление статуса жалобы.
    
    Доступ: moderator и выше
    """
    complaint = ComplaintRepository.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Жалоба не найдена"
        )
    
    # Бан пользователя
    success = UserRepository.ban_user(complaint.reported_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Обновление статуса жалобы
    ComplaintRepository.update_status(complaint_id, ComplaintStatus.RESOLVED)
    
    # Добавление действия модератора
    ComplaintRepository.add_action(
        complaint_id=complaint_id,
        moderator_id=admin.id,
        action="ban",
        comment="Пользователь забанен по жалобе"
    )
    
    logger.info(
        f"Администратор {admin.id} забанил пользователя {complaint.reported_id} "
        f"по жалобе {complaint_id}"
    )
    
    return {
        "message": "Пользователь забанен",
        "complaint_id": complaint_id,
        "reported_user_id": complaint.reported_id
    }


@router.get("/pending/count")
async def get_pending_complaints_count(
    admin: User = Depends(get_current_admin)
):
    """
    Получение количества ожидающих обработки жалоб.
    
    Доступ: все администраторы
    """
    pending = ComplaintRepository.get_pending()
    return {"count": len(pending)}
