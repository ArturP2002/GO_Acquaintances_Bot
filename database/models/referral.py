"""
Модель реферальной системы.
Связи между пригласившими и приглашенными пользователями.
"""
from datetime import datetime
from peewee import Model, IntegerField, BooleanField, DateTimeField, ForeignKeyField

from core.database import get_database
from database.models.user import BaseModel, User


class Referral(BaseModel):
    """
    Модель реферальной связи.
    Связь между пользователем, который пригласил, и приглашенным пользователем.
    """
    inviter = ForeignKeyField(User, backref="referrals_sent", on_delete="CASCADE", help_text="Пользователь, который пригласил")
    invited = ForeignKeyField(User, backref="referrals_received", on_delete="CASCADE", unique=True, help_text="Приглашенный пользователь")
    reward_given = BooleanField(default=False, help_text="Выдана ли награда за реферала")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания реферальной связи")
    
    class Meta:
        table_name = "referrals"
        indexes = (
            (('inviter',), False),
            (('invited',), True),  # Уникальный индекс: один пользователь может быть приглашен только одним человеком
            (('reward_given',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"Referral(id={self.id}, inviter_id={self.inviter_id}, invited_id={self.invited_id}, reward_given={self.reward_given})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для модели
Referral.set_database(get_database())
