"""
Сервис для работы с рекламными кампаниями.
Бизнес-логика для отправки рекламы пользователям.
"""
import logging
from typing import List, Optional
from datetime import datetime

from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo

from database.repositories.advertisement_repo import AdvertisementRepository
from database.repositories.user_repo import UserRepository
from database.models.user import User
from database.models.advertisement import AdvertisementCampaign, AdvertisementMedia

# Настройка логирования
logger = logging.getLogger(__name__)


class AdvertisementService:
    """Сервис для работы с рекламными кампаниями."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис рекламных кампаний.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
        """
        self.bot = bot
        self.advertisement_repo = AdvertisementRepository()
        self.user_repo = UserRepository()
    
    async def send_advertisement_to_all_users(self, campaign_id: int) -> int:
        """
        Отправляет рекламную кампанию только owner'ам.
        
        Логика отправки:
        - Если есть медиа:
          - Если медиа одно и это фото - отправляет фото с подписью (текст рекламы)
          - Если медиа одно и это видео - отправляет видео с подписью (текст рекламы)
          - Если медиа несколько (до 10) - отправляет медиа-группу (media_group) с текстом в первом медиа
        - Если медиа нет - отправляет только текст
        
        Args:
            campaign_id: ID рекламной кампании
            
        Returns:
            Количество успешно отправленных сообщений
        """
        try:
            # Получаем кампанию
            campaign = self.advertisement_repo.get_by_id(campaign_id)
            if not campaign:
                logger.error(f"Рекламная кампания {campaign_id} не найдена")
                return 0
            
            # Получаем все медиа кампании (отсортированные по order)
            media_list = self.advertisement_repo.get_media_by_campaign(campaign_id)
            
            # Получаем всех owner'ов (пользователей с ролью OWNER)
            from database.models.settings import AdminUser
            from core.constants import AdminRole
            
            owner_users = list(
                User.select()
                .join(AdminUser)
                .where(
                    (AdminUser.role == AdminRole.OWNER) &
                    (User.is_banned == False) &
                    (User.is_active == True)
                )
            )
            
            logger.info(
                f"Начало отправки рекламной кампании {campaign_id} "
                f"({len(media_list)} медиа) для {len(owner_users)} owner'ов"
            )
            
            sent_count = 0
            failed_count = 0
            
            # Отправляем рекламу каждому owner'у
            for user in owner_users:
                try:
                    success = await self._send_advertisement_to_user(
                        user.telegram_id,
                        campaign,
                        media_list
                    )
                    
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.warning(
                        f"Ошибка при отправке рекламы пользователю {user.telegram_id}: {e}",
                        exc_info=True
                    )
                    failed_count += 1
                    continue
            
            # Обновляем last_sent_at после успешной отправки
            if sent_count > 0:
                self.advertisement_repo.update(
                    campaign_id,
                    last_sent_at=datetime.now()
                )
            
            logger.info(
                f"Отправка рекламной кампании {campaign_id} завершена: "
                f"успешно отправлено {sent_count} owner'ам, ошибок {failed_count}"
            )
            
            return sent_count
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке рекламной кампании {campaign_id}: {e}",
                exc_info=True
            )
            return 0
    
    async def _send_advertisement_to_user(
        self,
        telegram_id: int,
        campaign: AdvertisementCampaign,
        media_list: List[AdvertisementMedia]
    ) -> bool:
        """
        Отправляет рекламную кампанию конкретному пользователю.
        
        Args:
            telegram_id: Telegram ID пользователя
            campaign: Объект рекламной кампании
            media_list: Список медиа кампании
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        try:
            text = campaign.text if campaign.text else None
            
            # Если медиа нет - отправляем только текст
            if not media_list:
                if not text:
                    logger.warning(
                        f"Кампания {campaign.id} не имеет ни текста, ни медиа. Пропускаем."
                    )
                    return False
                
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=text
                )
                return True
            
            # Если медиа одно
            if len(media_list) == 1:
                media = media_list[0]
                
                if media.file_type == "photo":
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=media.file_id,
                        caption=text if text else None
                    )
                elif media.file_type == "video":
                    await self.bot.send_video(
                        chat_id=telegram_id,
                        video=media.file_id,
                        caption=text if text else None
                    )
                else:
                    logger.warning(
                        f"Неизвестный тип медиа: {media.file_type} для кампании {campaign.id}"
                    )
                    return False
                
                return True
            
            # Если медиа несколько (до 10) - отправляем медиа-группу
            if len(media_list) > 1:
                # Ограничиваем до 10 элементов (ограничение Telegram API)
                media_to_send = media_list[:10]
                
                # Формируем медиа-группу
                media_group = self.format_media_group(campaign, media_to_send)
                
                await self.bot.send_media_group(
                    chat_id=telegram_id,
                    media=media_group
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке рекламы пользователю {telegram_id}: {e}",
                exc_info=True
            )
            return False
    
    def format_media_group(
        self,
        campaign: AdvertisementCampaign,
        media_list: List[AdvertisementMedia]
    ) -> List[InputMediaPhoto | InputMediaVideo]:
        """
        Формирует медиа-группу для отправки.
        Текст рекламы добавляется в подпись первого медиа.
        
        Args:
            campaign: Объект рекламной кампании
            media_list: Список медиа (уже отсортированный по order)
            
        Returns:
            Список InputMediaPhoto или InputMediaVideo для отправки медиа-группы
        """
        media_group = []
        text = campaign.text if campaign.text else None
        
        for i, media in enumerate(media_list):
            # Текст добавляем только к первому медиа
            caption = text if (i == 0 and text) else None
            
            if media.file_type == "photo":
                media_group.append(
                    InputMediaPhoto(
                        media=media.file_id,
                        caption=caption
                    )
                )
            elif media.file_type == "video":
                media_group.append(
                    InputMediaVideo(
                        media=media.file_id,
                        caption=caption
                    )
                )
            else:
                logger.warning(
                    f"Пропущено медиа {media.id} с неизвестным типом: {media.file_type}"
                )
                continue
        
        return media_group
    
    def get_active_campaigns_for_time(self, hour: int, minute: int) -> List[AdvertisementCampaign]:
        """
        Получает активные рекламные кампании для отправки в указанное время.
        
        Args:
            hour: Час (0-23)
            minute: Минута (0-59)
            
        Returns:
            Список активных кампаний, у которых send_time совпадает с указанным временем
        """
        # Форматируем время в формате "HH:MM"
        time_str = f"{hour:02d}:{minute:02d}"
        
        # Получаем все активные кампании
        active_campaigns = self.advertisement_repo.get_active()
        
        # Фильтруем по времени отправки
        matching_campaigns = [
            campaign for campaign in active_campaigns
            if campaign.send_time == time_str
        ]
        
        return matching_campaigns
