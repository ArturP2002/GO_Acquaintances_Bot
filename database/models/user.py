"""
Модель пользователя.
Основная таблица пользователей системы.
"""
from datetime import datetime
from peewee import Model, IntegerField, CharField, BooleanField, DateTimeField, ForeignKeyField

from core.database import get_database


class BaseModel(Model):
    """Базовый класс для всех моделей."""
    
    class Meta:
        database = None  # Будет установлено динамически
        
    @classmethod
    def set_database(cls, db):
        """Устанавливает базу данных для модели."""
        cls._meta.database = db


class User(BaseModel):
    """
    Модель пользователя.
    Основная таблица пользователей системы.
    """
    telegram_id = IntegerField(unique=True, index=True, help_text="Telegram ID пользователя")
    username = CharField(max_length=255, null=True, help_text="Username пользователя в Telegram")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время регистрации")
    is_banned = BooleanField(default=False, index=True, help_text="Забанен ли пользователь")
    is_verified = BooleanField(default=False, index=True, help_text="Верифицирован ли профиль")
    is_active = BooleanField(default=True, help_text="Активен ли пользователь")
    role = CharField(max_length=50, default="user", help_text="Роль пользователя")
    last_active = DateTimeField(null=True, help_text="Дата и время последней активности")
    
    class Meta:
        table_name = "users"
        indexes = (
            (('telegram_id',), True),  # Уникальный индекс на telegram_id
            (('is_banned',), False),
            (('is_verified',), False),
        )
    
    def __str__(self):
        return f"User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для модели
User.set_database(get_database())
