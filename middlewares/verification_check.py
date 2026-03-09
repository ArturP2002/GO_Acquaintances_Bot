"""
Middleware для проверки верификации пользователя.
Блокирует обработку запросов от неверифицированных пользователей.
"""
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.filters import Command

logger = logging.getLogger(__name__)


class VerificationCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки верификации пользователя.
    
    Проверяет флаг is_verified в записи пользователя из БД.
    Если пользователь не верифицирован, блокирует обработку запроса.
    Исключения: команда /start и регистрация.
    """
    
    def __init__(self, verification_message: str = "⏳ Ваша анкета находится на модерации.\n\nПожалуйста, дождитесь проверки модератором. Вы получите уведомление, когда ваша анкета будет одобрена."):
        """
        Инициализация middleware.
        
        Args:
            verification_message: Сообщение, которое отправляется неверифицированному пользователю
        """
        self.verification_message = verification_message
        # Команды и тексты, которые доступны без верификации
        self.allowed_commands = ["start", "register"]
        self.allowed_texts = ["Регистрация"]
    
    def _is_allowed(self, event: TelegramObject) -> bool:
        """
        Проверяет, разрешен ли запрос без верификации.
        
        Args:
            event: Событие Telegram
            
        Returns:
            True если запрос разрешен, False в противном случае
        """
        if isinstance(event, Message):
            # Проверяем команды
            if event.text:
                # Проверяем, является ли это командой /start или /register
                if event.text.startswith("/start") or event.text.startswith("/register"):
                    return True
                # Проверяем текст "Регистрация"
                if event.text in self.allowed_texts:
                    return True
        elif isinstance(event, CallbackQuery):
            # Callback запросы от неверифицированных пользователей блокируем
            # (кроме специальных случаев, которые можно добавить)
            pass
        
        return False
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка запроса с проверкой верификации.
        
        Args:
            handler: Обработчик запроса
            event: Событие Telegram
            data: Контекстные данные
            
        Returns:
            Результат обработки запроса или None, если пользователь не верифицирован
        """
        # Если запрос разрешен без верификации, пропускаем проверку
        if self._is_allowed(event):
            return await handler(event, data)
        
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
                # Пользователь является администратором - пропускаем проверку верификации
                return await handler(event, data)
            except AdminUser.DoesNotExist:
                # Пользователь не является администратором - продолжаем проверку
                pass
        except Exception as e:
            logger.warning(f"Ошибка при проверке прав администратора в VerificationCheckMiddleware: {e}")
            # В случае ошибки продолжаем проверку верификации
        
        # Проверяем флаг is_verified
        try:
            is_verified = getattr(user, "is_verified", False)
            
            if not is_verified:
                logger.info(f"Запрос от неверифицированного пользователя {user.telegram_id} заблокирован")
                
                # Пытаемся отправить сообщение пользователю
                try:
                    if isinstance(event, Message):
                        await event.answer(self.verification_message)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(self.verification_message, show_alert=True)
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение о верификации: {e}")
                
                # Блокируем обработку запроса
                return None
        except Exception as e:
            logger.error(f"Ошибка при проверке верификации пользователя: {e}", exc_info=True)
            # В случае ошибки пропускаем проверку, чтобы не блокировать легитимных пользователей
            return await handler(event, data)
        
        # Пользователь верифицирован, продолжаем обработку
        return await handler(event, data)
