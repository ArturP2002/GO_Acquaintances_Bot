"""
Middleware для добавления пользователя из БД в контекст.
Загружает информацию о пользователе из базы данных и добавляет её в context.
"""
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseMiddleware):
    """
    Middleware для добавления пользователя из БД в контекст.
    
    Загружает запись пользователя из таблицы Users по telegram_id
    и добавляет её в context.data под ключом "user".
    """
    
    def _get_telegram_user_id(self, event: TelegramObject) -> int | None:
        """
        Извлекает telegram_id пользователя из события.
        
        Args:
            event: Событие Telegram
            
        Returns:
            telegram_id пользователя или None
        """
        if isinstance(event, Message):
            return event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            return event.from_user.id if event.from_user else None
        # Для других типов событий можно добавить обработку
        return None
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка запроса с загрузкой пользователя из БД.
        
        Args:
            handler: Обработчик запроса
            event: Событие Telegram
            data: Контекстные данные
            
        Returns:
            Результат обработки запроса
        """
        telegram_id = self._get_telegram_user_id(event)
        
        # Если не удалось определить пользователя, пропускаем запрос
        if telegram_id is None:
            return await handler(event, data)
        
        # Получаем базу данных из контекста (должна быть добавлена DatabaseMiddleware)
        database = data.get("database")
        if database is None:
            logger.warning("База данных не найдена в контексте. UserContextMiddleware должен быть после DatabaseMiddleware")
            return await handler(event, data)
        
        # Пытаемся импортировать модель User
        # Если модель еще не создана, просто пропускаем добавление пользователя
        try:
            from database.models.user import User
            
            # Загружаем пользователя из БД
            try:
                user = User.get(User.telegram_id == telegram_id)
                data["user"] = user
                logger.debug(f"Пользователь {telegram_id} загружен из БД")
            except User.DoesNotExist:
                # Пользователь не найден в БД - это нормально для новых пользователей
                data["user"] = None
                logger.debug(f"Пользователь {telegram_id} не найден в БД")
            except Exception as e:
                logger.error(f"Ошибка при загрузке пользователя {telegram_id}: {e}", exc_info=True)
                data["user"] = None
        except ImportError:
            # Модель User еще не создана - это нормально на ранних этапах разработки
            logger.debug("Модель User не найдена, пропускаем загрузку пользователя")
            data["user"] = None
        
        # Выполняем обработчик
        return await handler(event, data)
