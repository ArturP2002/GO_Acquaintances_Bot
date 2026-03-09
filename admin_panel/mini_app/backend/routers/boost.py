"""
API endpoints для управления бустами.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from admin_panel.mini_app.backend.dependencies import get_current_admin, require_admin
from admin_panel.mini_app.backend.schemas import BoostResponse, BoostCreate, BoostListResponse
from database.models.user import User
from database.repositories.boost_repo import BoostRepository
from database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=BoostResponse)
async def create_boost(
    boost_create: BoostCreate,
    admin: User = Depends(require_admin)
):
    """
    Создание буста для пользователя.
    
    Доступ: admin и выше
    """
    # Проверка существования пользователя
    user = UserRepository.get_by_id(boost_create.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Создание буста
    boost = BoostRepository.create(
        user_id=boost_create.user_id,
        boost_value=boost_create.boost_value,
        expires_at=boost_create.expires_at
    )
    
    logger.info(
        f"Администратор {admin.id} создал буст для пользователя {boost_create.user_id}: "
        f"boost_value={boost_create.boost_value}"
    )
    
    return BoostResponse.model_validate(boost)


@router.get("/user/{user_id}", response_model=BoostListResponse)
async def get_user_boosts(
    user_id: int,
    admin: User = Depends(get_current_admin)
):
    """
    Получение всех бустов пользователя.
    
    Доступ: все администраторы
    """
    # Проверка существования пользователя
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    boosts = BoostRepository.get_all_boosts(user_id)
    
    return BoostListResponse(
        boosts=[BoostResponse.model_validate(b) for b in boosts],
        total=len(boosts)
    )


@router.get("/user/{user_id}/active", response_model=BoostListResponse)
async def get_active_boosts(
    user_id: int,
    admin: User = Depends(get_current_admin)
):
    """
    Получение активных бустов пользователя.
    
    Доступ: все администраторы
    """
    # Проверка существования пользователя
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    boosts = BoostRepository.get_active_boosts(user_id)
    
    return BoostListResponse(
        boosts=[BoostResponse.model_validate(b) for b in boosts],
        total=len(boosts)
    )


@router.delete("/{boost_id}")
async def delete_boost(
    boost_id: int,
    admin: User = Depends(require_admin)
):
    """
    Удаление буста.
    
    Доступ: admin и выше
    """
    from database.models.boost import Boost
    
    try:
        boost = Boost.get_by_id(boost_id)
        boost.delete_instance()
        
        logger.info(f"Администратор {admin.id} удалил буст {boost_id}")
        
        return {"message": "Буст удален", "boost_id": boost_id}
    except Boost.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Буст не найден"
        )
