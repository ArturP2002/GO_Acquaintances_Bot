"""
Утилиты для работы с реферальными ссылками.
Генерация и парсинг реферальных ссылок.
"""
import logging
from typing import Optional

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link

logger = logging.getLogger(__name__)


def generate_referral_code(telegram_id: int) -> str:
    """
    Генерирует реферальный код на основе Telegram ID пользователя.
    
    Формат: ref_<telegram_id>
    Например: ref_123456789
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        str: Реферальный код (например, "ref_123456789")
    """
    return f"ref_{telegram_id}"


def parse_referral_code(args: str) -> Optional[str]:
    """
    Парсит реферальный код из аргументов команды /start.
    
    Поддерживает форматы:
    - /start ref_12345
    - /start?start=ref_12345 (Telegram deep link)
    
    Args:
        args: Аргументы команды /start
        
    Returns:
        str: Реферальный код или None если не найден/невалиден
    """
    if not args:
        return None
    
    # Удаляем пробелы
    args = args.strip()
    
    # Поддержка формата start=ref_12345 (Telegram deep link)
    if args.startswith("start="):
        args = args.replace("start=", "", 1)
    
    # Проверка формата реферального кода
    if args.startswith("ref_") and len(args) > 4:
        # Извлекаем код после "ref_"
        code_part = args[4:]
        # Проверяем, что после "ref_" есть только цифры/буквы
        if code_part.replace("_", "").replace("-", "").isalnum():
            return args
    
    return None


async def generate_referral_link(bot: Bot, telegram_id: int) -> str:
    """
    Генерирует полную реферальную ссылку для пользователя.
    
    Args:
        bot: Экземпляр бота для получения username
        telegram_id: Telegram ID пользователя
        
    Returns:
        str: Полная реферальная ссылка (например, "https://t.me/botname?start=ref_123456789")
    """
    referral_code = generate_referral_code(telegram_id)
    
    try:
        # Используем aiogram для создания deep link
        link = await create_start_link(bot, referral_code)
        return link
    except Exception as e:
        logger.error(f"Ошибка при генерации реферальной ссылки: {e}")
        # Fallback: создаем ссылку вручную
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        return f"https://t.me/{bot_username}?start={referral_code}"


def extract_telegram_id_from_code(referral_code: str) -> Optional[int]:
    """
    Извлекает Telegram ID из реферального кода.
    
    Args:
        referral_code: Реферальный код (например, "ref_123456789")
        
    Returns:
        int: Telegram ID или None если код невалиден
    """
    if not referral_code or not referral_code.startswith("ref_"):
        return None
    
    try:
        # Извлекаем ID после "ref_"
        telegram_id_str = referral_code[4:]
        telegram_id = int(telegram_id_str)
        return telegram_id
    except (ValueError, IndexError):
        logger.warning(f"Не удалось извлечь Telegram ID из кода: {referral_code}")
        return None
