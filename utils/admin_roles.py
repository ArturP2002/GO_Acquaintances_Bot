"""
Утилиты для работы с ролями администраторов.
Проверка прав доступа и иерархии ролей.
"""
import logging
from typing import Optional

from database.models.user import User
from database.models.settings import AdminUser
from core.constants import AdminRole

logger = logging.getLogger(__name__)

# Иерархия ролей (чем выше число, тем больше прав)
ROLE_HIERARCHY = {
    AdminRole.OWNER: 4,
    AdminRole.ADMIN: 3,
    AdminRole.MODERATOR: 2,
    AdminRole.SUPPORT: 1
}


def get_user_role(user: User) -> Optional[str]:
    """
    Получает роль администратора для пользователя.
    
    Args:
        user: Объект пользователя
        
    Returns:
        Роль администратора или None если пользователь не является администратором
    """
    try:
        admin_user = AdminUser.get(AdminUser.user_id == user.id)
        return admin_user.role
    except AdminUser.DoesNotExist:
        return None


def get_role_level(role: str) -> int:
    """
    Получает уровень роли в иерархии.
    
    Args:
        role: Роль администратора
        
    Returns:
        Уровень роли (0 если роль неизвестна)
    """
    return ROLE_HIERARCHY.get(role, 0)


def has_role_or_higher(user: User, required_role: str) -> bool:
    """
    Проверяет, имеет ли пользователь требуемую роль или выше.
    
    Args:
        user: Объект пользователя
        required_role: Требуемая роль
        
    Returns:
        True если пользователь имеет требуемую роль или выше, False в противном случае
    """
    user_role = get_user_role(user)
    if user_role is None:
        return False
    
    user_level = get_role_level(user_role)
    required_level = get_role_level(required_role)
    
    return user_level >= required_level


def has_exact_role(user: User, role: str) -> bool:
    """
    Проверяет, имеет ли пользователь точно указанную роль.
    
    Args:
        user: Объект пользователя
        role: Требуемая роль
        
    Returns:
        True если пользователь имеет точно указанную роль, False в противном случае
    """
    user_role = get_user_role(user)
    return user_role == role


def can_manage_admins(user: User) -> bool:
    """
    Проверяет, может ли пользователь управлять администраторами.
    Только owner может управлять администраторами.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может управлять администраторами
    """
    return has_exact_role(user, AdminRole.OWNER)


def can_manage_settings(user: User) -> bool:
    """
    Проверяет, может ли пользователь управлять настройками.
    Owner и Admin могут управлять настройками.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может управлять настройками
    """
    return has_role_or_higher(user, AdminRole.ADMIN)


def can_ban_users(user: User) -> bool:
    """
    Проверяет, может ли пользователь банить пользователей.
    Owner, Admin и Moderator могут банить пользователей.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может банить пользователей
    """
    return has_role_or_higher(user, AdminRole.MODERATOR)


def can_manage_complaints(user: User) -> bool:
    """
    Проверяет, может ли пользователь управлять жалобами.
    Owner, Admin и Moderator могут управлять жалобами.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может управлять жалобами
    """
    return has_role_or_higher(user, AdminRole.MODERATOR)


def can_view_data(user: User) -> bool:
    """
    Проверяет, может ли пользователь просматривать данные.
    Все администраторы могут просматривать данные.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может просматривать данные
    """
    return get_user_role(user) is not None


def can_reset_likes(user: User) -> bool:
    """
    Проверяет, может ли пользователь сбрасывать лайки.
    Owner и Admin могут сбрасывать лайки.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может сбрасывать лайки
    """
    return has_role_or_higher(user, AdminRole.ADMIN)


def can_add_boost(user: User) -> bool:
    """
    Проверяет, может ли пользователь добавлять бусты.
    Owner и Admin могут добавлять бусты.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может добавлять бусты
    """
    return has_role_or_higher(user, AdminRole.ADMIN)


def can_verify_users(user: User) -> bool:
    """
    Проверяет, может ли пользователь верифицировать пользователей.
    Owner и Admin могут верифицировать пользователей.
    
    Args:
        user: Объект пользователя
        
    Returns:
        True если пользователь может верифицировать пользователей
    """
    return has_role_or_higher(user, AdminRole.ADMIN)
