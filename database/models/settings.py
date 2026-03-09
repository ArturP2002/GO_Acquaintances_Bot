"""
Модели настроек и администраторов.
Содержит модели Settings и AdminUsers.
"""
from datetime import datetime
from peewee import Model, IntegerField, CharField, TextField, DateTimeField, ForeignKeyField

from core.database import get_database
from core.constants import AdminRole
from database.models.user import BaseModel, User


class Settings(BaseModel):
    """
    Модель глобальных настроек системы.
    Хранит настройки бота (лимиты, частоты и т.д.).
    """
    key = CharField(max_length=100, unique=True, index=True, help_text="Ключ настройки")
    value = TextField(help_text="Значение настройки")
    updated_at = DateTimeField(default=datetime.now, help_text="Дата и время последнего обновления")
    
    class Meta:
        table_name = "settings"
        indexes = (
            (('key',), True),  # Уникальный индекс на key
        )
    
    def save(self, *args, **kwargs):
        """Переопределяем save для автоматического обновления updated_at."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Settings(id={self.id}, key={self.key}, value={self.value})"
    
    def __repr__(self):
        return self.__str__()


class AdminUser(BaseModel):
    """
    Модель администратора.
    Пользователи с правами администратора, модератора или поддержки.
    """
    user = ForeignKeyField(User, backref="admin_role", on_delete="CASCADE", unique=True, help_text="Пользователь")
    role = CharField(max_length=50, default=AdminRole.SUPPORT, index=True, help_text="Роль администратора (из AdminRole)")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время назначения роли")
    
    class Meta:
        table_name = "admin_users"
        indexes = (
            (('user',), True),  # Уникальный индекс на user (один пользователь = одна роль)
            (('role',), False),
        )
    
    def __str__(self):
        return f"AdminUser(id={self.id}, user_id={self.user_id}, role={self.role})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для моделей
Settings.set_database(get_database())
AdminUser.set_database(get_database())
