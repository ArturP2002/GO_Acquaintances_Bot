"""
Репозиторий для работы с рекламными кампаниями.
Слой доступа к данным для моделей AdvertisementCampaign и AdvertisementMedia.
"""
from typing import Optional, List
from datetime import datetime

from database.models.advertisement import AdvertisementCampaign, AdvertisementMedia


class AdvertisementRepository:
    """Репозиторий для работы с рекламными кампаниями."""
    
    # ========== Методы для кампаний ==========
    
    @staticmethod
    def create(text: Optional[str], send_time: str, created_by_user_id: int, 
               is_active: bool = True) -> AdvertisementCampaign:
        """
        Создает новую рекламную кампанию.
        
        Args:
            text: Текст рекламы (может быть None, если только медиа)
            send_time: Время отправки в формате "HH:MM"
            created_by_user_id: ID owner, создавшего кампанию
            is_active: Активна ли кампания (по умолчанию True)
            
        Returns:
            Созданный объект AdvertisementCampaign
        """
        return AdvertisementCampaign.create(
            text=text,
            send_time=send_time,
            created_by_user_id=created_by_user_id,
            is_active=is_active
        )
    
    @staticmethod
    def get_all() -> List[AdvertisementCampaign]:
        """
        Получает все рекламные кампании.
        
        Returns:
            Список всех кампаний, отсортированных по дате создания (новые первыми)
        """
        return list(
            AdvertisementCampaign.select()
            .order_by(AdvertisementCampaign.created_at.desc())
        )
    
    @staticmethod
    def get_active() -> List[AdvertisementCampaign]:
        """
        Получает все активные рекламные кампании.
        
        Returns:
            Список активных кампаний, отсортированных по дате создания (новые первыми)
        """
        return list(
            AdvertisementCampaign.select()
            .where(AdvertisementCampaign.is_active == True)
            .order_by(AdvertisementCampaign.created_at.desc())
        )
    
    @staticmethod
    def get_by_id(campaign_id: int) -> Optional[AdvertisementCampaign]:
        """
        Получает рекламную кампанию по ID.
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            AdvertisementCampaign или None если не найдена
        """
        try:
            return AdvertisementCampaign.get_by_id(campaign_id)
        except AdvertisementCampaign.DoesNotExist:
            return None
    
    @staticmethod
    def update(campaign_id: int, **kwargs) -> bool:
        """
        Обновляет рекламную кампанию.
        
        Args:
            campaign_id: ID кампании
            **kwargs: Поля для обновления (text, send_time, is_active, last_sent_at)
            
        Returns:
            True если обновление успешно, False если кампания не найдена
        """
        try:
            campaign = AdvertisementCampaign.get_by_id(campaign_id)
            for key, value in kwargs.items():
                if hasattr(campaign, key):
                    setattr(campaign, key, value)
            campaign.save()
            return True
        except AdvertisementCampaign.DoesNotExist:
            return False
    
    @staticmethod
    def delete(campaign_id: int) -> bool:
        """
        Удаляет рекламную кампанию.
        Медиа удаляются автоматически благодаря каскадному удалению (on_delete="CASCADE").
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            True если удаление успешно, False если кампания не найдена
        """
        try:
            campaign = AdvertisementCampaign.get_by_id(campaign_id)
            campaign.delete_instance()
            return True
        except AdvertisementCampaign.DoesNotExist:
            return False
    
    @staticmethod
    def toggle_active(campaign_id: int) -> Optional[bool]:
        """
        Переключает статус активности кампании (включить/выключить).
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            Новое значение is_active или None если кампания не найдена
        """
        try:
            campaign = AdvertisementCampaign.get_by_id(campaign_id)
            campaign.is_active = not campaign.is_active
            campaign.save()
            return campaign.is_active
        except AdvertisementCampaign.DoesNotExist:
            return None
    
    # ========== Методы для медиа ==========
    
    @staticmethod
    def add_media(campaign_id: int, file_id: str, file_type: str, order: int = 0) -> AdvertisementMedia:
        """
        Добавляет медиа к рекламной кампании.
        
        Args:
            campaign_id: ID рекламной кампании
            file_id: File ID медиа файла из Telegram
            file_type: Тип файла ("photo" или "video")
            order: Порядок отправки медиа (по умолчанию 0)
            
        Returns:
            Созданный объект AdvertisementMedia
        """
        return AdvertisementMedia.create(
            campaign_id=campaign_id,
            file_id=file_id,
            file_type=file_type,
            order=order
        )
    
    @staticmethod
    def get_media_by_campaign(campaign_id: int) -> List[AdvertisementMedia]:
        """
        Получает все медиа рекламной кампании, отсортированные по порядку отправки.
        
        Args:
            campaign_id: ID рекламной кампании
            
        Returns:
            Список медиа кампании, отсортированных по полю order
        """
        return list(
            AdvertisementMedia.select()
            .where(AdvertisementMedia.campaign_id == campaign_id)
            .order_by(AdvertisementMedia.order)
        )
    
    @staticmethod
    def get_media_by_id(media_id: int) -> Optional[AdvertisementMedia]:
        """
        Получает медиа по ID.
        
        Args:
            media_id: ID медиа
            
        Returns:
            AdvertisementMedia или None если не найдено
        """
        try:
            return AdvertisementMedia.get_by_id(media_id)
        except AdvertisementMedia.DoesNotExist:
            return None
    
    @staticmethod
    def delete_media(media_id: int) -> bool:
        """
        Удаляет медиа из рекламной кампании.
        
        Args:
            media_id: ID медиа
            
        Returns:
            True если удаление успешно, False если медиа не найдено
        """
        try:
            media = AdvertisementMedia.get_by_id(media_id)
            media.delete_instance()
            return True
        except AdvertisementMedia.DoesNotExist:
            return False
    
    @staticmethod
    def reorder_media(media_id: int, new_order: int) -> bool:
        """
        Изменяет порядок медиа в рекламной кампании.
        
        Args:
            media_id: ID медиа
            new_order: Новый порядок отправки
            
        Returns:
            True если обновление успешно, False если медиа не найдено
        """
        try:
            media = AdvertisementMedia.get_by_id(media_id)
            media.order = new_order
            media.save()
            return True
        except AdvertisementMedia.DoesNotExist:
            return False
