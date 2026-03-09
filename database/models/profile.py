"""
Модели профилей пользователей.
Содержит модели Profiles и ProfileMedia.
"""
from datetime import datetime
from peewee import Model, IntegerField, CharField, TextField, DateTimeField, ForeignKeyField, BooleanField

from core.database import get_database
from database.models.user import BaseModel, User


class Profile(BaseModel):
    """
    Модель профиля пользователя.
    Информация анкеты пользователя.
    """
    user = ForeignKeyField(User, backref="profile", on_delete="CASCADE", unique=True, help_text="Пользователь")
    name = CharField(max_length=255, help_text="Имя пользователя")
    age = IntegerField(index=True, help_text="Возраст пользователя")
    gender = CharField(max_length=20, help_text="Пол пользователя")
    city = CharField(max_length=255, null=True, index=True, help_text="Город пользователя")
    bio = TextField(null=True, help_text="Описание профиля")
    min_age_preference = IntegerField(default=18, help_text="Минимальный возраст для поиска")
    max_age_preference = IntegerField(default=100, help_text="Максимальный возраст для поиска")
    filter_by_opposite_gender = BooleanField(default=True, help_text="Фильтровать по противоположному полу")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания профиля")
    updated_at = DateTimeField(default=datetime.now, help_text="Дата и время последнего обновления")
    
    class Meta:
        table_name = "profiles"
        indexes = (
            (('age',), False),
            (('city',), False),
            (('user',), True),  # Уникальный индекс на user (1:1 связь)
        )
    
    def save(self, *args, **kwargs):
        """Переопределяем save для автоматического обновления updated_at."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Profile(id={self.id}, user_id={self.user_id}, name={self.name}, age={self.age})"
    
    def __repr__(self):
        return self.__str__()


class ProfileMedia(BaseModel):
    """
    Модель медиа профиля.
    Фото и кружки (video notes) пользователя.
    """
    profile = ForeignKeyField(Profile, backref="media", on_delete="CASCADE", help_text="Профиль")
    photo_file_id = CharField(max_length=255, null=True, help_text="File ID фото в Telegram")
    video_note_file_id = CharField(max_length=255, null=True, help_text="File ID кружка (video note) в Telegram")
    is_main = BooleanField(default=False, help_text="Является ли это главным фото")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время загрузки")
    
    class Meta:
        table_name = "profile_media"
        indexes = (
            (('profile', 'is_main'), False),
        )
    
    def __str__(self):
        return f"ProfileMedia(id={self.id}, profile_id={self.profile_id}, is_main={self.is_main})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для моделей
Profile.set_database(get_database())
ProfileMedia.set_database(get_database())
