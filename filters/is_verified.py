"""
Фильтр для проверки верификации пользователя.
Проверяет, что пользователь прошел модерацию (is_verified = True).
"""
import logging
from typing import Any

from aiogram.filters.base import Filter
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class IsVerified(Filter):
    """
    Фильтр для проверки верификации пользователя.
    
    Проверяет флаг is_verified в записи пользователя из БД.
    Пользователь должен быть верифицирован (прошел модерацию) для доступа к функциям.
    """
    
    async def __call__(
        self,
        obj: TelegramObject,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Проверка верификации пользователя.
        
        Args:
            obj: Событие Telegram
            data: Контекстные данные (должен содержать "user")
            
        Returns:
            True если пользователь верифицирован,
            False в противном случае
        """
        # Если data не предоставлен, возвращаем False
        if data is None:
            logger.debug("Контекстные данные не предоставлены для проверки верификации")
            return False
        
        # Получаем пользователя из контекста (должен быть добавлен UserContextMiddleware)
        user = data.get("user")
        
        # Если пользователь не загружен, фильтр не проходит
        if user is None:
            logger.debug("Пользователь не найден в контексте для проверки верификации")
            return False
        
        # Проверяем флаг is_verified
        # Предполагаем, что у модели User есть поле is_verified
        try:
            is_verified = getattr(user, "is_verified", False)
            
            if not is_verified:
                user_id = getattr(user, "telegram_id", "unknown")
                logger.debug(f"Пользователь {user_id} не верифицирован")
                return False
            
            logger.debug(f"Пользователь {getattr(user, 'telegram_id', 'unknown')} верифицирован")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при проверке верификации пользователя: {e}", exc_info=True)
            # В случае ошибки возвращаем False для безопасности
            return False
