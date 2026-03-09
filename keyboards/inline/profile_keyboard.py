"""
Inline клавиатуры для просмотра анкет.
Кнопки для действий с анкетами: лайк, пропуск, назад, жалоба.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_profile_keyboard(profile_id: int, user_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для просмотра анкеты.
    
    Args:
        profile_id: ID профиля, который просматривается
        user_id: ID пользователя, которому принадлежит профиль (для лайка и жалобы)
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❤️ Лайк",
                callback_data=f"like:{user_id}"
            ),
            InlineKeyboardButton(
                text="👎 Пропустить",
                callback_data="skip_profile"
            )
        ],
        [
            InlineKeyboardButton(
                text="↩ Назад",
                callback_data="back_profile"
            ),
            InlineKeyboardButton(
                text="🚨 Жалоба",
                callback_data=f"complaint:{user_id}"
            )
        ]
    ])
    
    return keyboard


def get_next_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой "Следующая анкета".
    Используется для начала просмотра анкет.
    
    Returns:
        InlineKeyboardMarkup с кнопкой "Следующая анкета"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➡️ Следующая анкета",
                callback_data="show_next_profile"
            )
        ]
    ])
    
    return keyboard


def get_like_notification_keyboard(from_user_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для уведомления о лайке.
    Пользователь может просмотреть анкету того, кто поставил лайк, или пропустить.
    
    Args:
        from_user_id: ID пользователя, который поставил лайк (в БД, не telegram_id)
        
    Returns:
        InlineKeyboardMarkup с кнопками "Просмотреть анкету" и "Пропустить"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👤 Просмотреть анкету",
                callback_data=f"view_liker_profile:{from_user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏭ Пропустить",
                callback_data=f"skip_like_notification:{from_user_id}"
            )
        ]
    ])
    
    return keyboard
