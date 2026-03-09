"""
Фильтры для проверки доступа.
Используются в обработчиках для ограничения доступа к функциям.
"""
from .is_admin import IsAdmin
from .is_verified import IsVerified
from .not_banned import NotBanned

__all__ = [
    "IsAdmin",
    "IsVerified",
    "NotBanned",
]
