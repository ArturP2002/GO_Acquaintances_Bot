"""
Inline клавиатуры для жалоб.
Кнопки для выбора причины жалобы и действий администраторов.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.constants import ComplaintReason


def get_complaint_reason_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора причины жалобы.
    
    Returns:
        InlineKeyboardMarkup с кнопками причин жалоб
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔞 18+",
                callback_data=f"complaint_reason:{ComplaintReason.ADULT_CONTENT}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💊 Наркотики",
                callback_data=f"complaint_reason:{ComplaintReason.DRUGS}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🤖 Фейк",
                callback_data=f"complaint_reason:{ComplaintReason.FAKE}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Оскорбления",
                callback_data=f"complaint_reason:{ComplaintReason.HARASSMENT}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❓ Другое",
                callback_data=f"complaint_reason:{ComplaintReason.OTHER}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="complaint_cancel"
            )
        ]
    ])
    
    return keyboard


def get_complaint_description_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для ввода описания жалобы (с возможностью пропустить).
    
    Returns:
        InlineKeyboardMarkup с кнопкой "Пропустить"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⏭ Пропустить",
                callback_data="complaint_skip_description"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="complaint_cancel"
            )
        ]
    ])
    
    return keyboard


def get_admin_complaint_keyboard(complaint_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для действий администратора по жалобе.
    
    Args:
        complaint_id: ID жалобы
        
    Returns:
        InlineKeyboardMarkup с кнопками действий администратора
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚫 Бан",
                callback_data=f"admin_complaint_ban:{complaint_id}"
            ),
            InlineKeyboardButton(
                text="✅ Отклонить",
                callback_data=f"admin_complaint_dismiss:{complaint_id}"
            )
        ]
    ])
    
    return keyboard
