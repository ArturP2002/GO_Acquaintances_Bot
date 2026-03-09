"""
API endpoints для управления пользователями.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from admin_panel.mini_app.backend.dependencies import get_current_admin, require_admin, require_moderator
from admin_panel.mini_app.backend.schemas import (
    UserResponse, UserUpdate, UserSearch, UserListResponse, ProfileResponse
)
from database.models.user import User
from database.models.profile import Profile
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    admin: User = Depends(get_current_admin)
):
    """
    Получение информации о текущем пользователе.
    
    Доступ: все администраторы
    """
    try:
        return UserResponse.model_validate(admin)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении информации о пользователе: {str(e)}"
        )


@router.get("/", response_model=UserListResponse)
async def get_users(
    telegram_id: Optional[int] = Query(None, description="Поиск по Telegram ID"),
    username: Optional[str] = Query(None, description="Поиск по username"),
    is_banned: Optional[bool] = Query(None, description="Фильтр по статусу бана"),
    is_verified: Optional[bool] = Query(None, description="Фильтр по верификации"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    admin: User = Depends(get_current_admin)
):
    """
    Получение списка пользователей с фильтрацией и пагинацией.
    
    Доступ: все администраторы
    """
    try:
        # Построение запроса
        query = User.select()
        
        if telegram_id:
            query = query.where(User.telegram_id == telegram_id)
        if username:
            query = query.where(User.username.contains(username))
        if is_banned is not None:
            query = query.where(User.is_banned == is_banned)
        if is_verified is not None:
            query = query.where(User.is_verified == is_verified)
        
        # Подсчет общего количества
        total = query.count()
        
        # Пагинация
        offset = (page - 1) * page_size
        users = list(query.offset(offset).limit(page_size))
        
        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка пользователей"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    admin: User = Depends(get_current_admin)
):
    """
    Получение информации о пользователе по ID.
    
    Доступ: все администраторы
    """
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return UserResponse.model_validate(user)


@router.get("/{user_id}/profile", response_model=ProfileResponse)
async def get_user_profile(
    user_id: int,
    admin: User = Depends(get_current_admin)
):
    """
    Получение профиля пользователя.
    
    Доступ: все администраторы
    """
    profile = ProfileRepository.get_by_user_id(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль пользователя не найден"
        )
    
    return ProfileResponse.model_validate(profile)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin: User = Depends(require_admin)
):
    """
    Обновление данных пользователя (бан, верификация, активность).
    
    Доступ: admin и выше
    """
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Обновление полей
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.save()
    
    logger.info(f"Администратор {admin.id} обновил пользователя {user_id}: {update_data}")
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: int,
    admin: User = Depends(require_moderator)
):
    """
    Бан пользователя.
    
    Доступ: moderator и выше
    """
    success = UserRepository.ban_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user = UserRepository.get_by_id(user_id)
    logger.info(f"Администратор {admin.id} забанил пользователя {user_id}")
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/unban", response_model=UserResponse)
async def unban_user(
    user_id: int,
    admin: User = Depends(require_moderator)
):
    """
    Разбан пользователя.
    
    Доступ: moderator и выше
    """
    success = UserRepository.unban_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user = UserRepository.get_by_id(user_id)
    logger.info(f"Администратор {admin.id} разбанил пользователя {user_id}")
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/reset-likes")
async def reset_user_likes(
    user_id: int,
    admin: User = Depends(require_admin)
):
    """
    Сброс лайков пользователя (для админов).
    Удаляет все лайки, поставленные пользователем.
    
    Доступ: admin и выше
    """
    from database.models.like import Like
    from database.repositories.like_repo import LikeRepository
    
    # Проверка существования пользователя
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Подсчет лайков до удаления
    likes_count = Like.select().where(Like.from_user_id == user_id).count()
    
    # Удаление всех лайков пользователя
    Like.delete().where(Like.from_user_id == user_id).execute()
    
    logger.info(
        f"Администратор {admin.id} сбросил {likes_count} лайков пользователя {user_id}"
    )
    
    return {
        "message": "Лайки пользователя сброшены",
        "user_id": user_id,
        "likes_deleted": likes_count
    }
