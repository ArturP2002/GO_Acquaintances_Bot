"""
Фильтр для проверки отсутствия бана пользователя.
Проверяет, что пользователь не забанен (is_banned = False).
"""
import logging
from typing import Any

from aiogram.filters.base import Filter
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class NotBanned(Filter):
    """
    Фильтр для проверки отсутствия бана пользователя.
    
    Проверяет флаг is_banned в записи пользователя из БД.
    Пользователь не должен быть забанен для доступа к функциям.
    """
    
    async def __call__(
        self,
        obj: TelegramObject,
        data: dict[str, Any],
    ) -> bool:
        """
        Проверка отсутствия бана пользователя.
        
        Args:
            obj: Событие Telegram
            data: Контекстные данные (должен содержать "user")
            
        Returns:
            True если пользователь не забанен,
            False в противном случае
        """
        # Получаем пользователя из контекста (должен быть добавлен UserContextMiddleware)
        user = data.get("user")
        
        # Если пользователь не загружен, фильтр не проходит
        if user is None:
            logger.debug("Пользователь не найден в контексте для проверки бана")
            return False
        
        # Проверяем флаг is_banned
        # Предполагаем, что у модели User есть поле is_banned
        try:
            is_banned = getattr(user, "is_banned", False)
            
            if is_banned:
                user_id = getattr(user, "telegram_id", "unknown")
                logger.debug(f"Пользователь {user_id} забанен")
                return False
            
            logger.debug(f"Пользователь {getattr(user, 'telegram_id', 'unknown')} не забанен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при проверке бана пользователя: {e}", exc_info=True)
            # В случае ошибки возвращаем False для безопасности
            return False
