"""
Middleware для защиты от спама.
Ограничивает частоту запросов от одного пользователя.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама.
    
    Ограничивает частоту запросов: максимум 1 запрос в секунду от одного пользователя.
    """
    
    def __init__(self, rate_limit: float = 1.0):
        """
        Инициализация middleware.
        
        Args:
            rate_limit: Минимальный интервал между запросами в секундах (по умолчанию 1.0)
        """
        self.rate_limit = rate_limit
        # Словарь для хранения времени последнего запроса каждого пользователя
        # Ключ: user_id, Значение: timestamp последнего запроса
        self.last_request_time: dict[int, float] = {}
        # Словарь для хранения задач ожидания (для предотвращения одновременных запросов)
        self.pending_requests: dict[int, asyncio.Task] = {}
    
    def _get_user_id(self, event: TelegramObject) -> int | None:
        """
        Извлекает ID пользователя из события.
        
        Args:
            event: Событие Telegram
            
        Returns:
            ID пользователя или None, если не удалось извлечь
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
        Обработка запроса с проверкой лимита частоты.
        
        Args:
            handler: Обработчик запроса
            event: Событие Telegram
            data: Контекстные данные
            
        Returns:
            Результат обработки запроса или None, если запрос был заблокирован
        """
        user_id = self._get_user_id(event)
        
        # Если не удалось определить пользователя, пропускаем запрос
        if user_id is None:
            return await handler(event, data)
        
        current_time = time.time()
        last_time = self.last_request_time.get(user_id, 0)
        time_since_last_request = current_time - last_time
        
        # Если прошло недостаточно времени с последнего запроса
        if time_since_last_request < self.rate_limit:
            wait_time = self.rate_limit - time_since_last_request
            
            # Если есть уже ожидающий запрос от этого пользователя, отменяем его
            if user_id in self.pending_requests:
                pending_task = self.pending_requests[user_id]
                if not pending_task.done():
                    pending_task.cancel()
            
            # Создаем задачу ожидания
            wait_task = asyncio.create_task(asyncio.sleep(wait_time))
            self.pending_requests[user_id] = wait_task
            
            try:
                await wait_task
            except asyncio.CancelledError:
                # Запрос был отменен новым запросом
                logger.debug(f"Запрос от пользователя {user_id} отменен из-за нового запроса")
                return None
            
            # Удаляем задачу из словаря
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]
        
        # Обновляем время последнего запроса
        self.last_request_time[user_id] = time.time()
        
        # Очищаем старые записи (старше 1 часа) для экономии памяти
        if len(self.last_request_time) > 10000:
            cutoff_time = current_time - 3600  # 1 час назад
            self.last_request_time = {
                uid: timestamp
                for uid, timestamp in self.last_request_time.items()
                if timestamp > cutoff_time
            }
        
        # Выполняем обработчик
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}", exc_info=True)
            raise
