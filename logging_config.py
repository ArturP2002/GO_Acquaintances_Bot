"""
Настройка логирования для бота.
Конфигурация логов с разными уровнями и форматами.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO", log_file: str = "bot.log") -> None:
    """
    Настраивает систему логирования для бота.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов
    """
    # Создаем директорию для логов если не существует
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Формат логов
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очистка существующих обработчиков
    root_logger.handlers.clear()
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # Настройка уровней для сторонних библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('peewee').setLevel(logging.WARNING)
    
    logging.info(f"Логирование настроено. Уровень: {log_level}, Файл: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер с указанным именем.
    
    Args:
        name: Имя логгера (обычно __name__)
        
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


# Логгеры для разных модулей
registration_logger = get_logger('registration')
moderation_logger = get_logger('moderation')
matching_logger = get_logger('matching')
likes_logger = get_logger('likes')
complaints_logger = get_logger('complaints')
admin_logger = get_logger('admin')
