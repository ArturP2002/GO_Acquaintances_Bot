"""
Модели модерации.
Содержит модели ModerationQueue и ModerationActions.
"""
from datetime import datetime
from peewee import Model, IntegerField, CharField, TextField, DateTimeField, ForeignKeyField

from core.database import get_database
from core.constants import ModerationStatus
from database.models.user import BaseModel, User
from database.models.profile import Profile


class ModerationQueue(BaseModel):
    """
    Модель очереди модерации.
    Задачи модерации профилей (кружки, фото).
    """
    user = ForeignKeyField(User, backref="moderation_tasks", on_delete="CASCADE", help_text="Пользователь")
    profile = ForeignKeyField(Profile, backref="moderation_tasks", on_delete="CASCADE", help_text="Профиль на модерации")
    task = CharField(max_length=255, help_text="Задание для кружка (например, 'Покажи 👍')")
    status = CharField(max_length=50, default=ModerationStatus.PENDING, index=True, help_text="Статус модерации (из ModerationStatus)")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время создания задачи")
    moderated_at = DateTimeField(null=True, help_text="Дата и время модерации")
    
    class Meta:
        table_name = "moderation_queue"
        indexes = (
            (('user',), False),
            (('profile',), False),
            (('status',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"ModerationQueue(id={self.id}, user_id={self.user_id}, profile_id={self.profile_id}, status={self.status})"
    
    def __repr__(self):
        return self.__str__()


class ModerationAction(BaseModel):
    """
    Модель действия модератора.
    Лог действий модераторов по обработке задач модерации.
    """
    moderation = ForeignKeyField(ModerationQueue, backref="actions", on_delete="CASCADE", help_text="Задача модерации")
    moderator = ForeignKeyField(User, backref="moderation_actions", on_delete="CASCADE", help_text="Модератор, который выполнил действие")
    action = CharField(max_length=100, help_text="Действие (approve, reject, ban, etc.)")
    comment = TextField(null=True, help_text="Комментарий модератора")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время действия")
    
    class Meta:
        table_name = "moderation_actions"
        indexes = (
            (('moderation',), False),
            (('moderator',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"ModerationAction(id={self.id}, moderation_id={self.moderation_id}, moderator_id={self.moderator_id}, action={self.action})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для моделей
ModerationQueue.set_database(get_database())
ModerationAction.set_database(get_database())
