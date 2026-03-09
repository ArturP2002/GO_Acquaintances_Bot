"""
Клавиатура главного меню для зарегистрированных пользователей.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from config import config


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру главного меню.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками главного меню
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="💕 Смотреть анкеты"), KeyboardButton(text="❤️ Мои симпатии")],
            [KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


def get_registration_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для незарегистрированных пользователей.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой регистрации
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Регистрация")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_owner_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру главного меню для owner с кнопкой Mini App.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками для owner, включая Mini App
    """
    keyboard_buttons = [
        [KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="💕 Смотреть анкеты"), KeyboardButton(text="❤️ Мои симпатии")],
        [KeyboardButton(text="⚙️ Настройки")]
    ]
    
    # Добавляем кнопку Mini App, если URL начинается с https://
    mini_app_url = getattr(config, 'MINI_APP_URL', 'http://localhost:3000')
    if mini_app_url and mini_app_url.startswith('https://'):
        keyboard_buttons.append([
            KeyboardButton(
                text="🌐 Mini App",
                web_app=WebAppInfo(url=mini_app_url)
            )
        ])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard
