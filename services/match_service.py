"""
Сервис для работы с мэтчами (взаимными симпатиями).
Создание мэтчей и отправка уведомлений пользователям.
"""
import logging
from typing import Optional, Tuple, List

from aiogram import Bot

from database.repositories.match_repo import MatchRepository
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.models.match import Match
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id

# Настройка логирования
logger = logging.getLogger(__name__)


class MatchService:
    """Сервис для работы с мэтчами."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис мэтчей.
        
        Args:
            bot: Экземпляр бота для отправки уведомлений
        """
        self.bot = bot
        self.match_repo = MatchRepository()
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
    
    def create_match(self, user1_id: int, user2_id: int) -> Tuple[Optional[Match], bool]:
        """
        Создает мэтч между двумя пользователями.
        Проверяет, не существует ли уже мэтч, и создает новый если его нет.
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            
        Returns:
            Tuple[Optional[Match], bool]:
            - Первый элемент: Созданный или существующий объект Match
            - Второй элемент: True если мэтч был создан только что, False если уже существовал
        """
        # Проверяем, не существует ли уже мэтч
        if self.match_repo.exists(user1_id, user2_id):
            logger.debug(f"Мэтч между пользователями {user1_id} и {user2_id} уже существует")
            match = self.match_repo.get(user1_id, user2_id)
            return match, False
        
        # Создаем мэтч
        match = self.match_repo.create(user1_id, user2_id)
        logger.info(f"Создан мэтч между пользователями {user1_id} и {user2_id}")
        
        return match, True
    
    async def notify_users_about_match(self, user1_id: int, user2_id: int) -> None:
        """
        Отправляет уведомления обоим пользователям о мэтче.
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
        """
        try:
            # Получаем пользователей
            user1 = self.user_repo.get_by_id(user1_id)
            user2 = self.user_repo.get_by_id(user2_id)
            
            if not user1 or not user2:
                logger.error(f"Не удалось найти пользователей для уведомления о мэтче: user1_id={user1_id}, user2_id={user2_id}")
                return
            
            # Получаем профили
            profile1 = self.profile_repo.get_by_user_id(user1_id)
            profile2 = self.profile_repo.get_by_user_id(user2_id)
            
            if not profile1 or not profile2:
                logger.error(f"Не удалось найти профили для уведомления о мэтче: user1_id={user1_id}, user2_id={user2_id}")
                return
            
            # Формируем сообщения для обоих пользователей
            # Уведомление для user1 о мэтче с user2
            profile2_text = format_profile_text(profile2)
            profile2_photo = get_profile_photo_file_id(profile2)
            
            match_message1 = (
                "🎉 У вас взаимная симпатия!\n\n"
                f"{profile2_text}"
            )
            
            # Уведомление для user2 о мэтче с user1
            profile1_text = format_profile_text(profile1)
            profile1_photo = get_profile_photo_file_id(profile1)
            
            match_message2 = (
                "🎉 У вас взаимная симпатия!\n\n"
                f"{profile1_text}"
            )
            
            # Отправляем уведомления
            try:
                if profile2_photo:
                    await self.bot.send_photo(
                        chat_id=user1.telegram_id,
                        photo=profile2_photo,
                        caption=match_message1
                    )
                else:
                    await self.bot.send_message(
                        chat_id=user1.telegram_id,
                        text=match_message1
                    )
                logger.info(f"Уведомление о мэтче отправлено пользователю {user1_id} (telegram_id={user1.telegram_id})")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления о мэтче пользователю {user1_id}: {e}")
            
            try:
                if profile1_photo:
                    await self.bot.send_photo(
                        chat_id=user2.telegram_id,
                        photo=profile1_photo,
                        caption=match_message2
                    )
                else:
                    await self.bot.send_message(
                        chat_id=user2.telegram_id,
                        text=match_message2
                    )
                logger.info(f"Уведомление о мэтче отправлено пользователю {user2_id} (telegram_id={user2.telegram_id})")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления о мэтче пользователю {user2_id}: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений о мэтче: {e}", exc_info=True)
    
    def get_user_matches(self, user_id: int) -> List[Match]:
        """
        Получает список мэтчей пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список мэтчей пользователя
        """
        return self.match_repo.get_user_matches(user_id)
