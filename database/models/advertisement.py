"""
Модели рекламных кампаний.
Содержит модели AdvertisementCampaign и AdvertisementMedia.
"""
from datetime import datetime
from peewee import Model, CharField, TextField, DateTimeField, ForeignKeyField, BooleanField, IntegerField

from core.database import get_database
from database.models.user import BaseModel, User


class AdvertisementCampaign(BaseModel):
    """
    Модель рекламной кампании.
    Хранит информацию о рекламных кампаниях для автоматической отправки пользователям.
    """
    text = TextField(null=True, help_text="Текст рекламы (может быть пустым, если только медиа)")
    send_time = CharField(max_length=5, help_text="Время отправки в формате HH:MM")
    is_active = BooleanField(default=True, index=True, help_text="Активна ли кампания")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания кампании")
    created_by_user = ForeignKeyField(User, backref="advertisement_campaigns", on_delete="CASCADE", help_text="Owner, создавший кампанию")
    last_sent_at = DateTimeField(null=True, help_text="Дата и время последней отправки")
    
    class Meta:
        table_name = "advertisement_campaigns"
        indexes = (
            (('is_active',), False),
            (('send_time',), False),
            (('created_by_user',), False),
        )
    
    def __str__(self):
        return f"AdvertisementCampaign(id={self.id}, send_time={self.send_time}, is_active={self.is_active})"
    
    def __repr__(self):
        return self.__str__()


class AdvertisementMedia(BaseModel):
    """
    Модель медиа рекламной кампании.
    Фото и видео для рекламных кампаний.
    """
    campaign = ForeignKeyField(AdvertisementCampaign, backref="media", on_delete="CASCADE", help_text="Рекламная кампания")
    file_id = CharField(max_length=255, help_text="File ID медиа файла из Telegram")
    file_type = CharField(max_length=10, help_text="Тип файла: 'photo' или 'video'")
    order = IntegerField(default=0, help_text="Порядок отправки медиа")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время добавления медиа")
    
    class Meta:
        table_name = "advertisement_media"
        indexes = (
            (('campaign', 'order'), False),
            (('campaign',), False),
        )
    
    def __str__(self):
        return f"AdvertisementMedia(id={self.id}, campaign_id={self.campaign_id}, file_type={self.file_type}, order={self.order})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для моделей
AdvertisementCampaign.set_database(get_database())
AdvertisementMedia.set_database(get_database())
