"""
Модель бустов анкет.
Система повышения приоритета показа анкет.
"""
from datetime import datetime
from peewee import Model, IntegerField, DateTimeField, ForeignKeyField

from core.database import get_database
from database.models.user import BaseModel, User


class Boost(BaseModel):
    """
    Модель буста анкеты.
    Бусты повышают приоритет показа анкеты в алгоритме выдачи.
    """
    user = ForeignKeyField(User, backref="boosts", on_delete="CASCADE", help_text="Пользователь")
    boost_value = IntegerField(default=0, help_text="Значение буста (0=обычный, 1=реферальный, 3=платный)")
    expires_at = DateTimeField(null=True, index=True, help_text="Дата и время истечения буста")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания буста")
    
    class Meta:
        table_name = "boosts"
        indexes = (
            (('user',), False),
            (('expires_at',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"Boost(id={self.id}, user_id={self.user_id}, boost_value={self.boost_value}, expires_at={self.expires_at})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для модели
Boost.set_database(get_database())
