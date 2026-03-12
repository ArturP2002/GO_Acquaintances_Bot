"""
Inline клавиатуры для админ-панели.
Кнопки для управления пользователями, настройками, жалобами, рекламой и администраторами.
"""
from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from core.constants import AdminRole
from utils.admin_roles import (
    get_user_role,
    can_manage_admins,
    can_manage_settings,
    can_ban_users,
    can_reset_likes,
    can_add_boost,
    can_verify_users
)
from database.models.user import User
from config import config


def get_admin_main_keyboard(user: Optional[User] = None) -> InlineKeyboardMarkup:
    """
    Создает главную клавиатуру админ-панели.
    
    Args:
        user: Пользователь для проверки прав (опционально)
    
    Returns:
        InlineKeyboardMarkup с основными разделами админки
    """
    buttons = []
    
    # Пользователи - доступны всем администраторам
    buttons.append([
        InlineKeyboardButton(
            text="👥 Пользователи",
            callback_data="admin:users"
        )
    ])
    
    # Настройки - только admin и выше
    if user is None or can_manage_settings(user):
        buttons.append([
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="admin:settings"
            )
        ])
    
    # Жалобы - доступны всем администраторам
    buttons.append([
        InlineKeyboardButton(
            text="🚨 Жалобы",
            callback_data="admin:complaints"
        )
    ])
    
    # Реклама - временно доступна всем администраторам (для тестирования)
    buttons.append([
        InlineKeyboardButton(
            text="📢 Реклама",
            callback_data="admin:advertisements"
        )
    ])
    
    # Администраторы - только owner
    if user is None or can_manage_admins(user):
        buttons.append([
            InlineKeyboardButton(
                text="👑 Администраторы",
                callback_data="admin:admins"
            )
        ])
    
    # Статистика - доступна всем администраторам
    buttons.append([
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin:stats"
        )
    ])
    
    # Бэкап базы данных - только admin и выше
    if user is None or can_manage_settings(user):
        buttons.append([
            InlineKeyboardButton(
                text="💾 Бэкап БД",
                callback_data="admin:backup"
            )
        ])
    
    # Mini App - доступна всем администраторам
    # Получаем URL из конфига (по умолчанию http://localhost:3000)
    # Telegram требует только HTTPS для любых URL в кнопках
    # Для локальной разработки (http://localhost) кнопка не будет показана
    mini_app_url = getattr(config, 'MINI_APP_URL', 'http://localhost:3000')
    
    # Показываем кнопку Web App только если URL начинается с https://
    # Для локальной разработки кнопка не показывается вообще
    if mini_app_url and mini_app_url.startswith('https://'):
        buttons.append([
            InlineKeyboardButton(
                text="🌐 Открыть Mini App",
                web_app=WebAppInfo(url=mini_app_url)
            )
        ])
    # Для HTTP URL (локальная разработка) кнопка не показывается
    # Пользователь может открыть Mini App напрямую в браузере по адресу http://localhost:3000
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_user_actions_keyboard(user_id: int, user: Optional[User] = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий с пользователем.
    
    Args:
        user_id: ID пользователя
        user: Пользователь для проверки прав (опционально)
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    buttons = []
    
    # Бан/разбан - moderator и выше
    if user is None or can_ban_users(user):
        buttons.append([
            InlineKeyboardButton(
                text="🚫 Забанить",
                callback_data=f"admin:ban:{user_id}"
            ),
            InlineKeyboardButton(
                text="✅ Разбанить",
                callback_data=f"admin:unban:{user_id}"
            )
        ])
    
    # Верификация - admin и выше
    if user is None or can_verify_users(user):
        buttons.append([
            InlineKeyboardButton(
                text="✅ Верифицировать",
                callback_data=f"admin:verify:{user_id}"
            ),
            InlineKeyboardButton(
                text="❌ Снять верификацию",
                callback_data=f"admin:unverify:{user_id}"
            )
        ])
    
    # Сброс лайков и буст - admin и выше
    admin_buttons = []
    if user is None or can_reset_likes(user):
        admin_buttons.append(
            InlineKeyboardButton(
                text="🔄 Сбросить лайки",
                callback_data=f"admin:reset_likes:{user_id}"
            )
        )
    if user is None or can_add_boost(user):
        admin_buttons.append(
            InlineKeyboardButton(
                text="🚀 Добавить буст",
                callback_data=f"admin:boost:{user_id}"
            )
        )
    if admin_buttons:
        buttons.append(admin_buttons)
    
    # Кнопка уменьшения буста на отдельной строке
    if user is None or can_add_boost(user):
        buttons.append([
            InlineKeyboardButton(
                text="⬇️ Уменьшить буст",
                callback_data=f"admin:reduce_boost:{user_id}"
            )
        ])
    
    # Назад - доступен всем
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin:users"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления настройками.
    
    Returns:
        InlineKeyboardMarkup с кнопками настроек
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❤️ Лимит лайков",
                callback_data="admin:setting:max_likes_per_day"
            ),
            InlineKeyboardButton(
                text="🚀 Частота буста",
                callback_data="admin:setting:boost_frequency"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin:main"
            )
        ]
    ])
    
    return keyboard


def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления администраторами.
    
    Returns:
        InlineKeyboardMarkup с кнопками управления админами
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Добавить админа",
                callback_data="admin:add_admin"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin:main"
            )
        ]
    ])
    
    return keyboard


def get_admin_role_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора роли администратора.
    
    Args:
        admin_user_id: ID пользователя-администратора
        
    Returns:
        InlineKeyboardMarkup с кнопками ролей
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👑 Owner",
                callback_data=f"admin:set_role:{admin_user_id}:{AdminRole.OWNER}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🛡️ Admin",
                callback_data=f"admin:set_role:{admin_user_id}:{AdminRole.ADMIN}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔨 Moderator",
                callback_data=f"admin:set_role:{admin_user_id}:{AdminRole.MODERATOR}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Support",
                callback_data=f"admin:set_role:{admin_user_id}:{AdminRole.SUPPORT}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"admin:remove_admin:{admin_user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin:admins"
            )
        ]
    ])
    
    return keyboard


def get_confirm_keyboard(action: str, target_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру подтверждения действия.
    
    Args:
        action: Действие для подтверждения
        target_id: ID цели действия
        
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin:confirm:{action}:{target_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"admin:cancel:{action}:{target_id}"
            )
        ]
    ])
    
    return keyboard


def get_advertisements_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления рекламными кампаниями.
    
    Returns:
        InlineKeyboardMarkup с кнопками управления рекламой
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Создать рекламу",
                callback_data="admin:advertisement:create"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin:main"
            )
        ]
    ])
    
    return keyboard


def get_advertisement_actions_keyboard(campaign_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий с конкретной рекламной кампанией.
    
    Args:
        campaign_id: ID рекламной кампании
        is_active: Активна ли кампания (для отображения правильной иконки)
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    buttons = []
    
    # Редактирование текста
    buttons.append([
        InlineKeyboardButton(
            text="✏️ Редактировать текст",
            callback_data=f"admin:advertisement:edit_text:{campaign_id}"
        )
    ])
    
    # Медиа
    buttons.append([
        InlineKeyboardButton(
            text="🖼️ Медиа",
            callback_data=f"admin:advertisement:media:{campaign_id}"
        )
    ])
    
    # Время отправки
    buttons.append([
        InlineKeyboardButton(
            text="⏰ Время",
            callback_data=f"admin:advertisement:time:{campaign_id}"
        )
    ])
    
    # Включение/выключение
    toggle_text = "⏸️ Выключить" if is_active else "▶️ Включить"
    buttons.append([
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=f"admin:advertisement:toggle:{campaign_id}"
        )
    ])
    
    # Удаление
    buttons.append([
        InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"admin:advertisement:delete:{campaign_id}"
        )
    ])
    
    # Назад
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin:advertisements"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_advertisement_media_keyboard(campaign_id: int, media_list: list) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления медиа рекламной кампании.
    
    Args:
        campaign_id: ID рекламной кампании
        media_list: Список медиа объектов с полями id и order
        
    Returns:
        InlineKeyboardMarkup с кнопками управления медиа
    """
    buttons = []
    
    # Сортируем медиа по порядку
    sorted_media = sorted(media_list, key=lambda x: getattr(x, 'order', 0))
    
    # Кнопки для каждого медиа
    for idx, media in enumerate(sorted_media):
        media_id = getattr(media, 'id', None)
        if media_id is None:
            continue
            
        media_buttons = []
        
        # Кнопка "Вверх" (если не первое)
        if idx > 0:
            media_buttons.append(
                InlineKeyboardButton(
                    text="⬆️ Вверх",
                    callback_data=f"admin:advertisement:media_up:{campaign_id}:{media_id}"
                )
            )
        
        # Кнопка "Вниз" (если не последнее)
        if idx < len(sorted_media) - 1:
            media_buttons.append(
                InlineKeyboardButton(
                    text="⬇️ Вниз",
                    callback_data=f"admin:advertisement:media_down:{campaign_id}:{media_id}"
                )
            )
        
        # Кнопка "Удалить"
        media_buttons.append(
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"admin:advertisement:media_delete:{campaign_id}:{media_id}"
            )
        )
        
        if media_buttons:
            buttons.append(media_buttons)
    
    # Кнопка добавления медиа
    buttons.append([
        InlineKeyboardButton(
            text="➕ Добавить медиа",
            callback_data=f"admin:advertisement:media_add:{campaign_id}"
        )
    ])
    
    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"admin:advertisement:actions:{campaign_id}"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
