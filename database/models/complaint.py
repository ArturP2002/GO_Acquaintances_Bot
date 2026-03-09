"""
Модели жалоб.
Содержит модели Complaints и ComplaintActions.
"""
from datetime import datetime
from peewee import Model, IntegerField, CharField, TextField, DateTimeField, ForeignKeyField

from core.database import get_database
from core.constants import ComplaintStatus, ComplaintReason
from database.models.user import BaseModel, User


class Complaint(BaseModel):
    """
    Модель жалобы.
    Жалобы пользователей на других пользователей.
    """
    reporter = ForeignKeyField(User, backref="complaints_sent", on_delete="CASCADE", help_text="Пользователь, который подал жалобу")
    reported = ForeignKeyField(User, backref="complaints_received", on_delete="CASCADE", help_text="Пользователь, на которого пожаловались")
    reason = CharField(max_length=50, help_text="Причина жалобы (из ComplaintReason)")
    description = TextField(null=True, help_text="Описание жалобы")
    status = CharField(max_length=50, default=ComplaintStatus.PENDING, index=True, help_text="Статус жалобы (из ComplaintStatus)")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания жалобы")
    
    class Meta:
        table_name = "complaints"
        indexes = (
            (('reporter',), False),
            (('reported',), False),
            (('status',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"Complaint(id={self.id}, reporter={self.reporter_id}, reported={self.reported_id}, reason={self.reason})"
    
    def __repr__(self):
        return self.__str__()


class ComplaintAction(BaseModel):
    """
    Модель действия по жалобе.
    Лог действий модераторов по обработке жалоб.
    """
    complaint = ForeignKeyField(Complaint, backref="actions", on_delete="CASCADE", help_text="Жалоба")
    moderator = ForeignKeyField(User, backref="complaint_actions", on_delete="CASCADE", help_text="Модератор, который выполнил действие")
    action = CharField(max_length=100, help_text="Действие (ban, unban, dismiss, etc.)")
    comment = TextField(null=True, help_text="Комментарий модератора")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время действия")
    
    class Meta:
        table_name = "complaint_actions"
        indexes = (
            (('complaint',), False),
            (('moderator',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"ComplaintAction(id={self.id}, complaint_id={self.complaint_id}, moderator_id={self.moderator_id}, action={self.action})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для моделей
Complaint.set_database(get_database())
ComplaintAction.set_database(get_database())
