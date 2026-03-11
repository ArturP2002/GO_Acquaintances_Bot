"""
Reply клавиатуры для просмотра анкет.
Кнопки для действий с анкетами: лайк, пропуск, назад, жалоба.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_profile_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает reply-клавиатуру для просмотра анкеты с эмодзи-кнопками.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками действий (❤️, 👎, ↩, 🚨, 💤)
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❤️"),
                KeyboardButton(text="👎")
            ],
            [
                KeyboardButton(text="↩"),
                KeyboardButton(text="🚨")
            ],
            [
                KeyboardButton(text="💤")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    return keyboard
