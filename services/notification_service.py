"""
Сервис для отправки уведомлений пользователям.
Уведомления о новых мэтчах, напоминания неактивным пользователям.
"""
import logging
from datetime import datetime, timedelta
from typing import List

from aiogram import Bot
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.match_repo import MatchRepository
from database.models.user import User
from core.constants import ACTIVE_USER_THRESHOLD_DAYS

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений пользователям."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис уведомлений.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
        """
        self.bot = bot
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.match_repo = MatchRepository()
    
    async def notify_inactive_users(self) -> int:
        """
        Отправляет напоминания неактивным пользователям о новых анкетах.
        
        Returns:
            Количество отправленных уведомлений
        """
        try:
            logger.info("Запуск задачи уведомления неактивных пользователей...")
            
            # Получаем неактивных пользователей (не заходили более 3 дней)
            inactive_threshold = datetime.now() - timedelta(days=ACTIVE_USER_THRESHOLD_DAYS)
            
            inactive_users = list(
                User.select()
                .where(
                    (User.is_banned == False) &
                    (User.is_verified == True) &
                    (User.is_active == True) &
                    (
                        (User.last_active.is_null()) |
                        (User.last_active < inactive_threshold)
                    )
                )
            )
            
            logger.info(f"Найдено неактивных пользователей: {len(inactive_users)}")
            
            sent_count = 0
            
            for user in inactive_users:
                try:
                    # Проверяем, есть ли у пользователя профиль
                    profile = self.profile_repo.get_by_user_id(user.id)
                    if not profile:
                        continue
                    
                    # Отправляем напоминание
                    message = (
                        "👋 Привет! Мы соскучились!\n\n"
                        "💕 Мы подобрали для тебя новые анкеты.\n"
                        "Заходи и посмотри, может быть, твоя половинка уже ждет тебя!\n\n"
                        "Используй команду /start для начала просмотра анкет."
                    )
                    
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        disable_notification=False
                    )
                    
                    sent_count += 1
                    logger.debug(f"Отправлено напоминание неактивному пользователю {user.telegram_id}")
                    
                except Exception as e:
                    logger.warning(
                        f"Ошибка при отправке напоминания пользователю {user.telegram_id}: {e}"
                    )
                    continue
            
            logger.info(f"Задача уведомления неактивных пользователей завершена. Отправлено: {sent_count}")
            return sent_count
            
        except Exception as e:
            logger.error(
                f"Ошибка при выполнении задачи уведомления неактивных пользователей: {e}",
                exc_info=True
            )
            return 0
    
    async def notify_new_matches(self, user_id: int) -> bool:
        """
        Отправляет уведомление пользователю о новых мэтчах (если есть).
        
        Args:
            user_id: ID пользователя в БД
            
        Returns:
            True если уведомление отправлено, False иначе
        """
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return False
            
            # Получаем новые мэтчи (за последние 24 часа)
            recent_threshold = datetime.now() - timedelta(hours=24)
            recent_matches = self.match_repo.get_recent_matches(user_id, recent_threshold)
            
            if recent_matches:
                matches_count = len(recent_matches)
                message = (
                    f"🎉 У тебя {matches_count} новых взаимных симпатий!\n\n"
                    "Используй команду /matches или кнопку '❤️ Мои симпатии' "
                    "для просмотра."
                )
                
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    disable_notification=False
                )
                
                logger.info(f"Отправлено уведомление о новых мэтчах пользователю {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о новых мэтчах: {e}")
            return False
