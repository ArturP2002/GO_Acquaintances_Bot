"""
Middleware для управления контекстом базы данных.
Обеспечивает открытие и закрытие соединения с БД для каждого запроса.
"""
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject
from peewee import Database

from loader import get_database

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для управления соединением с базой данных.
    
    Открывает соединение с БД перед обработкой запроса
    и закрывает его после завершения обработки.
    """
    
    def __init__(self, database: Database | None = None):
        """
        Инициализация middleware.
        
        Args:
            database: Экземпляр базы данных. Если None, будет получен через get_database()
        """
        self.database = database
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка запроса с управлением соединением БД.
        
        Args:
            handler: Обработчик запроса
            event: Событие Telegram
            data: Контекстные данные
            
        Returns:
            Результат обработки запроса
        """
        # Получаем экземпляр базы данных
        db = self.database or get_database()
        
        # Добавляем базу данных в контекст
        data["database"] = db
        
        # Открываем соединение, если оно закрыто
        if db.is_closed():
            db.connect(reuse_if_open=True)
            logger.debug("Соединение с БД открыто")
        
        try:
            # Выполняем обработчик
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}", exc_info=True)
            raise
        finally:
            # Закрываем соединение после обработки
            # Для SQLite с WAL режимом это безопасно и не влияет на производительность
            if not db.is_closed():
                db.close()
                logger.debug("Соединение с БД закрыто")
