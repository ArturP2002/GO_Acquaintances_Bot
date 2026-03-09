"""
Модель мэтчей.
Взаимные симпатии между пользователями.
"""
from datetime import datetime
from peewee import Model, IntegerField, DateTimeField, ForeignKeyField

from core.database import get_database
from database.models.user import BaseModel, User


class Match(BaseModel):
    """
    Модель мэтча (взаимной симпатии).
    Создается когда два пользователя лайкнули друг друга.
    """
    user1 = ForeignKeyField(User, backref="matches_as_user1", on_delete="CASCADE", help_text="Первый пользователь")
    user2 = ForeignKeyField(User, backref="matches_as_user2", on_delete="CASCADE", help_text="Второй пользователь")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания мэтча")
    
    class Meta:
        table_name = "matches"
        indexes = (
            (('user1', 'user2'), True),  # Уникальный индекс: один мэтч между двумя пользователями
            (('user1',), False),
            (('user2',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"Match(id={self.id}, user1={self.user1_id}, user2={self.user2_id})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для модели
Match.set_database(get_database())
