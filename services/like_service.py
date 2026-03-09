"""
Сервис для работы с лайками.
Обработка лайков, проверка лимитов, создание мэтчей.
"""
import logging
from typing import Tuple, Optional

from aiogram import Bot

from database.repositories.like_repo import LikeRepository
from database.repositories.settings_repo import SettingsRepository
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from services.match_service import MatchService
from core.cache import invalidate_user_cache
from keyboards.inline.profile_keyboard import get_like_notification_keyboard
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id

# Настройка логирования
logger = logging.getLogger(__name__)


class LikeService:
    """Сервис для работы с лайками."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис лайков.
        
        Args:
            bot: Экземпляр бота для отправки уведомлений о мэтчах
        """
        self.bot = bot
        self.like_repo = LikeRepository()
        self.settings_repo = SettingsRepository()
        self.match_service = MatchService(bot)
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
    
    def add_like(self, from_user_id: int, to_user_id: int) -> Tuple[bool, Optional[str], bool, bool]:
        """
        Добавляет лайк от одного пользователя другому.
        Проверяет лимит лайков, создает лайк, проверяет мэтч.
        
        Args:
            from_user_id: ID пользователя, который ставит лайк
            to_user_id: ID пользователя, которому ставят лайк
            
        Returns:
            Tuple[bool, Optional[str], bool, bool]:
            - Первый элемент: True если лайк успешно добавлен, False если ошибка
            - Второй элемент: Сообщение об ошибке (если есть) или None
            - Третий элемент: True если есть мэтч, False если нет
            - Четвертый элемент: True если лайк был создан только что, False если уже существовал
        """
        # Проверка: нельзя лайкнуть самого себя
        if from_user_id == to_user_id:
            logger.warning(f"Попытка лайкнуть самого себя: user_id={from_user_id}")
            return False, "Нельзя лайкнуть самого себя", False, False
        
        # Проверка лимита лайков за сегодня
        max_likes_per_day = self.settings_repo.get_int('max_likes_per_day', default=50)
        likes_today = self.like_repo.count_today_likes(from_user_id)
        
        if likes_today >= max_likes_per_day:
            logger.info(f"Пользователь {from_user_id} превысил лимит лайков: {likes_today}/{max_likes_per_day}")
            return False, f"Лимит лайков на сегодня ({max_likes_per_day}) исчерпан", False, False
        
        # Проверка: не лайкали ли уже этого пользователя
        if self.like_repo.exists(from_user_id, to_user_id):
            logger.debug(f"Лайк от {from_user_id} к {to_user_id} уже существует")
            # Проверяем мэтч на случай, если он уже есть
            has_match = self.check_match(from_user_id, to_user_id)
            return True, None, has_match, False  # False - лайк уже существовал
        
        # Создаем лайк
        try:
            self.like_repo.create(from_user_id, to_user_id)
            logger.info(f"Создан лайк от {from_user_id} к {to_user_id}")
            
            # Инвалидируем кэш кандидатов для обоих пользователей
            invalidate_user_cache(from_user_id)
            invalidate_user_cache(to_user_id)
        except Exception as e:
            logger.error(f"Ошибка при создании лайка от {from_user_id} к {to_user_id}: {e}", exc_info=True)
            return False, "Ошибка при создании лайка", False, False
        
        # Проверяем взаимный лайк (мэтч)
        has_match = self.check_match(from_user_id, to_user_id)
        
        return True, None, has_match, True  # True - лайк был создан только что
    
    def check_match(self, from_user_id: int, to_user_id: int) -> bool:
        """
        Проверяет, есть ли взаимный лайк между двумя пользователями (мэтч).
        
        Args:
            from_user_id: ID первого пользователя
            to_user_id: ID второго пользователя
            
        Returns:
            True если есть взаимный лайк, False в противном случае
        """
        return self.like_repo.check_reciprocal(from_user_id, to_user_id)
    
    async def create_match(self, user1_id: int, user2_id: int) -> Optional[object]:
        """
        Создает мэтч между двумя пользователями и отправляет уведомления.
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            
        Returns:
            Созданный объект Match или существующий Match
        """
        # Создаем мэтч через match_service
        match, is_new = self.match_service.create_match(user1_id, user2_id)
        
        # Если мэтч был создан только что (не существовал ранее), отправляем уведомления
        if match and is_new:
            await self.match_service.notify_users_about_match(user1_id, user2_id)
        
        return match
    
    async def notify_about_like(self, from_user_id: int, to_user_id: int) -> bool:
        """
        Отправляет уведомление пользователю о том, что кто-то поставил ему лайк.
        Уведомление отправляется только если нет мэтча (при мэтче отправляется другое уведомление).
        
        Args:
            from_user_id: ID пользователя, который поставил лайк (в БД)
            to_user_id: ID пользователя, которому поставили лайк (в БД)
            
        Returns:
            True если уведомление успешно отправлено, False в противном случае
        """
        logger.info(f"Вызов notify_about_like: from_user_id={from_user_id}, to_user_id={to_user_id}")
        try:
            # Получаем пользователя, которому нужно отправить уведомление
            to_user = self.user_repo.get_by_id(to_user_id)
            if not to_user:
                logger.warning(f"Пользователь {to_user_id} не найден для отправки уведомления о лайке")
                return False
            
            logger.debug(f"Пользователь {to_user_id} найден, telegram_id={to_user.telegram_id}, is_banned={to_user.is_banned}")
            
            # Проверяем, не забанен ли пользователь
            if to_user.is_banned:
                logger.debug(f"Пользователь {to_user_id} забанен, уведомление о лайке не отправляется")
                return False
            
            # Получаем профиль пользователя, который поставил лайк
            from_profile = self.profile_repo.get_by_user_id(from_user_id)
            if not from_profile:
                logger.warning(f"Профиль пользователя {from_user_id} не найден для уведомления о лайке")
                return False
            
            # Формируем сообщение
            profile_name = from_profile.name
            profile_age = from_profile.age
            message_text = (
                f"❤️ <b>Вам поставили лайк!</b>\n\n"
                f"👤 {profile_name}, {profile_age}"
            )
            
            # Если есть город, добавляем его
            if from_profile.city:
                message_text += f"\n📍 {from_profile.city}"
            
            message_text += "\n\nХотите посмотреть анкету?"
            
            # Получаем фото профиля
            photo_file_id = get_profile_photo_file_id(from_profile)
            
            # Создаем клавиатуру
            keyboard = get_like_notification_keyboard(from_user_id)
            
            # Отправляем уведомление
            try:
                if photo_file_id:
                    # Отправляем фото с подписью
                    await self.bot.send_photo(
                        chat_id=to_user.telegram_id,
                        photo=photo_file_id,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Отправляем текстовое сообщение
                    await self.bot.send_message(
                        chat_id=to_user.telegram_id,
                        text=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                logger.info(f"Уведомление о лайке отправлено пользователю {to_user_id} от {from_user_id}")
                return True
            except Exception as e:
                logger.error(
                    f"Ошибка при отправке уведомления о лайке пользователю {to_user_id} "
                    f"(telegram_id={to_user.telegram_id}): {e}",
                    exc_info=True
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Ошибка при подготовке уведомления о лайке от {from_user_id} к {to_user_id}: {e}",
                exc_info=True
            )
            return False