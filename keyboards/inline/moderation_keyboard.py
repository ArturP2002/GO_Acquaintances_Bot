"""
Inline клавиатуры для модерации.
Кнопки для действий модераторов: подтверждение, отклонение, бан.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_moderation_keyboard(moderation_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для модерации профиля.
    
    Args:
        moderation_id: ID задачи модерации
        
    Returns:
        InlineKeyboardMarkup с кнопками модерации
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"moderation_approve:{moderation_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"moderation_reject:{moderation_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Бан",
                callback_data=f"moderation_ban:{moderation_id}"
            )
        ]
    ])
    
    return keyboard


def get_ai_moderation_keyboard(user_id: int, check_type: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для действий админов при обнаружении нарушений ИИ.
    
    Args:
        user_id: ID пользователя
        check_type: Тип нарушения (nudity, drugs, violence, general)
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👁 Проверить",
                callback_data=f"ai_moderation:review:{user_id}:{check_type}"
            ),
            InlineKeyboardButton(
                text="🚫 Бан",
                callback_data=f"ai_moderation:ban:{user_id}:{check_type}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✔ Разрешить",
                callback_data=f"ai_moderation:allow:{user_id}:{check_type}"
            )
        ]
    ])
    
    return keyboard


def get_ai_decision_keyboard(user_id: int, check_type: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для оценки решения ИИ админами.
    
    Args:
        user_id: ID пользователя
        check_type: Тип нарушения (nudity, drugs, violence, general)
        
    Returns:
        InlineKeyboardMarkup с кнопками для оценки решения ИИ
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👁 Просмотр профиля",
                callback_data=f"ai_moderation:review:{user_id}:{check_type}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Решение верно",
                callback_data=f"ai_decision:correct:{user_id}:{check_type}"
            ),
            InlineKeyboardButton(
                text="❌ Решение неверно",
                callback_data=f"ai_decision:incorrect:{user_id}:{check_type}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Забанить",
                callback_data=f"ai_moderation:ban:{user_id}:{check_type}"
            ),
            InlineKeyboardButton(
                text="✔ Разрешить",
                callback_data=f"ai_moderation:allow:{user_id}:{check_type}"
            )
        ]
    ])
    
    return keyboard
