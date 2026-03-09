"""
Зависимости для FastAPI endpoints.
Включает проверку авторизации, прав доступа и подключение к БД.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from database.models.user import User
from database.models.settings import AdminUser
from core.constants import AdminRole
from core.database import get_database as get_db_connection

logger = logging.getLogger(__name__)

# Делаем security опциональным для лучшей обработки ошибок
security = HTTPBearer(auto_error=False)


async def get_database():
    """Получение подключения к БД."""
    from core.database import init_database
    
    # Инициализация БД (если еще не инициализирована)
    db = init_database()
    
    # Убеждаемся, что соединение открыто
    if db.is_closed():
        try:
            db.connect(reuse_if_open=True)
            logger.debug("БД переподключена в get_database()")
        except Exception as e:
            logger.error(f"Ошибка при подключении к БД: {e}", exc_info=True)
            raise
    
    return db


async def get_current_user(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Получение текущего пользователя из токена авторизации.
    
    В Mini App Telegram передает initData, который содержит информацию о пользователе.
    Здесь должна быть реализована проверка подписи initData и извлечение user_id.
    
    Args:
        authorization: Токен авторизации из заголовка
        
    Returns:
        User объект текущего пользователя
        
    Raises:
        HTTPException: Если пользователь не авторизован или не найден
    """
    try:
        # TODO: Реализовать проверку initData от Telegram Mini App
        # Пока используем заголовок X-Telegram-User-ID для разработки
        # В продакшене нужно проверять подпись initData
        
        if not authorization:
            logger.warning("Попытка доступа без токена авторизации")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен авторизации не предоставлен"
            )
        
        token = authorization.credentials
        
        if not token:
            logger.warning("Токен авторизации пустой")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен авторизации не предоставлен"
            )
        
        # Временная реализация: ожидаем telegram_id в токене
        # В продакшене нужно декодировать initData и проверить подпись
        try:
            telegram_id = int(token)
            logger.debug(f"Получен telegram_id из токена: {telegram_id}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Неверный формат токена: {token}, ошибка: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный формат токена"
            )
        
        # Убеждаемся, что БД подключена
        await get_database()
        
        # Получаем пользователя из БД
        from database.repositories.user_repo import UserRepository
        user = UserRepository.get_by_telegram_id(telegram_id)
        
        if not user:
            logger.warning(f"Пользователь с telegram_id {telegram_id} не найден в БД")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        logger.debug(f"Пользователь найден: {user.id}, telegram_id: {user.telegram_id}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении текущего пользователя: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


async def get_current_admin(
    current_user: User = Depends(get_current_user),
    required_role: Optional[str] = None
) -> User:
    """
    Получение текущего администратора с проверкой прав.
    
    Args:
        current_user: Текущий пользователь
        required_role: Требуемая роль (owner/admin/moderator/support)
        
    Returns:
        User объект администратора
        
    Raises:
        HTTPException: Если пользователь не является администратором
    """
    try:
        # Убеждаемся, что БД подключена
        await get_database()
        
        admin_user = AdminUser.get(AdminUser.user_id == current_user.id)
        logger.debug(f"Администратор найден: user_id={current_user.id}, role={admin_user.role}")
    except AdminUser.DoesNotExist:
        logger.warning(f"Пользователь {current_user.id} не является администратором")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при проверке прав доступа: {str(e)}"
        )
    
    # Проверка конкретной роли, если указана
    if required_role:
        role_hierarchy = {
            AdminRole.OWNER: 4,
            AdminRole.ADMIN: 3,
            AdminRole.MODERATOR: 2,
            AdminRole.SUPPORT: 1
        }
        
        user_role_level = role_hierarchy.get(admin_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)
        
        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещен. Требуется роль: {required_role}"
            )
    
    # Возвращаем User объект, а не AdminUser
    return current_user


# Зависимости для проверки конкретных ролей
async def require_owner(admin: User = Depends(get_current_admin)) -> User:
    """Требует роль owner."""
    try:
        admin_user = AdminUser.get(AdminUser.user_id == admin.id)
        if admin_user.role != AdminRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуется роль owner."
            )
    except AdminUser.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    return admin


async def require_admin(admin: User = Depends(get_current_admin)) -> User:
    """Требует роль admin или выше."""
    try:
        admin_user = AdminUser.get(AdminUser.user_id == admin.id)
        if admin_user.role not in [AdminRole.OWNER, AdminRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуется роль admin или выше."
            )
    except AdminUser.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    return admin


async def require_moderator(admin: User = Depends(get_current_admin)) -> User:
    """Требует роль moderator или выше."""
    try:
        admin_user = AdminUser.get(AdminUser.user_id == admin.id)
        if admin_user.role not in [AdminRole.OWNER, AdminRole.ADMIN, AdminRole.MODERATOR]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуется роль moderator или выше."
            )
    except AdminUser.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    return admin
