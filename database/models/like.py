"""
Модель лайков.
Содержит модели Likes, ProfileViews и ProfileHistory.
"""
from datetime import datetime
from peewee import Model, IntegerField, DateTimeField, ForeignKeyField

from core.database import get_database
from database.models.user import BaseModel, User
from database.models.profile import Profile


class Like(BaseModel):
    """
    Модель лайка.
    Лайки между пользователями.
    """
    from_user = ForeignKeyField(User, backref="likes_sent", on_delete="CASCADE", help_text="Пользователь, который поставил лайк")
    to_user = ForeignKeyField(User, backref="likes_received", on_delete="CASCADE", help_text="Пользователь, которому поставили лайк")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время лайка")
    
    class Meta:
        table_name = "likes"
        indexes = (
            (('from_user', 'to_user'), True),  # Уникальный индекс: один пользователь может лайкнуть другого только один раз
            (('from_user',), False),
            (('to_user',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"Like(id={self.id}, from_user={self.from_user_id}, to_user={self.to_user_id})"
    
    def __repr__(self):
        return self.__str__()


class ProfileView(BaseModel):
    """
    Модель просмотра анкеты.
    Отслеживание просмотренных анкет для исключения повторного показа.
    """
    viewer = ForeignKeyField(User, backref="profile_views", on_delete="CASCADE", help_text="Пользователь, который просмотрел анкету")
    profile = ForeignKeyField(Profile, backref="views", on_delete="CASCADE", help_text="Просмотренный профиль")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время просмотра")
    
    class Meta:
        table_name = "profile_views"
        indexes = (
            (('viewer', 'profile'), True),  # Уникальный индекс: один пользователь может просмотреть анкету только один раз
            (('viewer',), False),
            (('profile',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"ProfileView(id={self.id}, viewer_id={self.viewer_id}, profile_id={self.profile_id})"
    
    def __repr__(self):
        return self.__str__()


class ProfileHistory(BaseModel):
    """
    Модель истории просмотров анкет.
    Используется для кнопки "Назад" при листании анкет.
    """
    user = ForeignKeyField(User, backref="profile_history", on_delete="CASCADE", help_text="Пользователь")
    profile = ForeignKeyField(Profile, backref="history_entries", on_delete="CASCADE", help_text="Профиль из истории")
    position = IntegerField(help_text="Позиция в истории (для навигации назад)")
    created_at = DateTimeField(default=datetime.now, help_text="Дата и время добавления в историю")
    
    class Meta:
        table_name = "profile_history"
        indexes = (
            (('user', 'position'), False),
            (('user',), False),
            (('profile',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"ProfileHistory(id={self.id}, user_id={self.user_id}, profile_id={self.profile_id}, position={self.position})"
    
    def __repr__(self):
        return self.__str__()


# Устанавливаем базу данных для моделей
Like.set_database(get_database())
ProfileView.set_database(get_database())
ProfileHistory.set_database(get_database())
