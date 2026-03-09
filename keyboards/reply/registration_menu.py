"""
Клавиатура для процесса регистрации.
Кнопки для навигации во время регистрации.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_registration_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для незарегистрированных пользователей.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой регистрации
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Начать регистрацию")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_gender_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для выбора пола.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с вариантами пола
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру только с кнопкой отмены.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
