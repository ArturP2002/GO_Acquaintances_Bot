"""
Middleware для проверки бана пользователя.
Блокирует обработку запросов от забаненных пользователей.
"""
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class BanCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки бана пользователя.
    
    Проверяет флаг is_banned в записи пользователя из БД.
    Если пользователь забанен, блокирует обработку запроса.
    Исключения: команда /start (чтобы пользователь мог увидеть сообщение о бане).
    """
    
    def __init__(self, ban_message: str = "🚫 Вы были заблокированы. Обратитесь к администратору."):
        """
        Инициализация middleware.
        
        Args:
            ban_message: Сообщение, которое отправляется забаненному пользователю
        """
        self.ban_message = ban_message
        # Команды, которые доступны даже забаненным пользователям (только для просмотра сообщения о бане)
        self.allowed_commands = ["start"]
    
    def _is_allowed(self, event: TelegramObject) -> bool:
        """
        Проверяет, разрешен ли запрос для забаненного пользователя.
        
        Args:
            event: Событие Telegram
            
        Returns:
            True если запрос разрешен, False в противном случае
        """
        if isinstance(event, Message):
            # Разрешаем только команду /start, чтобы пользователь мог увидеть сообщение о бане
            if event.text and event.text.startswith("/start"):
                return True
        # Все остальные запросы блокируем для забаненных пользователей
        return False
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка запроса с проверкой бана.
        
        Args:
            handler: Обработчик запроса
            event: Событие Telegram
            data: Контекстные данные
            
        Returns:
            Результат обработки запроса или None, если пользователь забанен
        """
        # Получаем пользователя из контекста (должен быть добавлен UserContextMiddleware)
        user = data.get("user")
        
        # Если пользователь не загружен, пропускаем проверку
        # (это может быть новый пользователь или ошибка загрузки)
        if user is None:
            return await handler(event, data)
        
        # Проверяем, является ли пользователь администратором
        # Администраторы не блокируются
        try:
            from database.models.settings import AdminUser
            try:
                admin_user = AdminUser.get(AdminUser.user_id == user.id)
                # Пользователь является администратором - пропускаем проверку бана
                return await handler(event, data)
            except AdminUser.DoesNotExist:
                # Пользователь не является администратором - продолжаем проверку
                pass
        except Exception as e:
            logger.warning(f"Ошибка при проверке прав администратора в BanCheckMiddleware: {e}")
            # В случае ошибки продолжаем проверку бана
        
        # Проверяем флаг is_banned
        # Предполагаем, что у модели User есть поле is_banned
        try:
            is_banned = getattr(user, "is_banned", False)
            
            if is_banned:
                # Если запрос разрешен (например, /start), пропускаем проверку
                if self._is_allowed(event):
                    return await handler(event, data)
                
                logger.info(f"Запрос от забаненного пользователя {user.telegram_id} заблокирован")
                
                # Пытаемся отправить сообщение пользователю
                try:
                    if isinstance(event, Message):
                        await event.answer(self.ban_message)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(self.ban_message, show_alert=True)
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение о бане: {e}")
                
                # Блокируем обработку запроса
                return None
        except Exception as e:
            logger.error(f"Ошибка при проверке бана пользователя: {e}", exc_info=True)
            # В случае ошибки пропускаем проверку, чтобы не блокировать легитимных пользователей
            return await handler(event, data)
        
        # Пользователь не забанен, продолжаем обработку
        return await handler(event, data)
