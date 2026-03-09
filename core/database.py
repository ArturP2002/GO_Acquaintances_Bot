"""
Модуль для работы с базой данных.
Обеспечивает подключение к SQLite через Peewee с настройкой пула соединений.

SQLite в Peewee использует singleton-паттерн для управления соединениями,
что обеспечивает эффективное переиспользование одного соединения.
"""
import logging
import os
import threading
from contextlib import contextmanager
from typing import Optional

from peewee import SqliteDatabase

from config import config
from core.constants import DATABASE_PRAGMAS

logger = logging.getLogger(__name__)

# Глобальный экземпляр базы данных
_database: Optional[SqliteDatabase] = None
# Блокировка для потокобезопасности
_database_lock = threading.Lock()


def get_database() -> SqliteDatabase:
    """
    Возвращает экземпляр базы данных (singleton).
    Если база данных еще не инициализирована, создает новое подключение.
    
    Для SQLite используется singleton-паттерн, который обеспечивает
    переиспользование одного соединения (аналог connection pooling).
    
    Returns:
        SqliteDatabase: Экземпляр базы данных Peewee
        
    Raises:
        RuntimeError: Если не удалось создать подключение к БД
    """
    global _database
    
    # Двойная проверка с блокировкой для потокобезопасности
    if _database is not None and not _database.is_closed():
        return _database
    
    with _database_lock:
        # Повторная проверка после получения блокировки
        if _database is not None and not _database.is_closed():
            return _database
        
        # Преобразуем относительный путь в абсолютный относительно корня проекта
        db_path = config.DATABASE_PATH
        if not os.path.isabs(db_path):
            # Получаем корень проекта (2 уровня вверх от core/database.py)
            # core/database.py -> core/ -> корень проекта
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            db_path = os.path.join(project_root, db_path)
        
        logger.info(f"Создание подключения к базе данных: {db_path}")
        
        try:
            # Создание подключения к SQLite с оптимизированными настройками
            # PRAGMAS настроены для лучшей производительности и безопасности
            _database = SqliteDatabase(
                db_path,
                pragmas=DATABASE_PRAGMAS,
                # Опции для лучшей работы с соединениями
                check_same_thread=False,  # Разрешаем использование из разных потоков
                timeout=20.0,  # Таймаут ожидания блокировки БД (в секундах)
            )
            
            logger.info("Подключение к базе данных успешно создано")
            logger.debug(f"PRAGMAS настроены: {DATABASE_PRAGMAS}")
            return _database
            
        except Exception as e:
            logger.error(f"Ошибка при создании подключения к БД: {e}", exc_info=True)
            raise RuntimeError(f"Не удалось создать подключение к базе данных: {e}")


def init_database() -> SqliteDatabase:
    """
    Инициализирует подключение к базе данных.
    Явно создает подключение, если оно еще не было создано.
    
    Returns:
        SqliteDatabase: Экземпляр базы данных
    """
    db = get_database()
    
    # Проверяем, что соединение действительно открыто
    if db.is_closed():
        logger.warning("Соединение с БД было закрыто, пересоздаем...")
        global _database
        with _database_lock:
            _database = None
        db = get_database()
    
    return db


def close_database():
    """
    Закрывает подключение к базе данных.
    Потокобезопасная операция.
    """
    global _database
    
    with _database_lock:
        if _database is not None and not _database.is_closed():
            logger.info("Закрытие подключения к базе данных...")
            try:
                _database.close()
                logger.info("Подключение к базе данных закрыто")
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединения с БД: {e}", exc_info=True)
            finally:
                _database = None


def is_database_initialized() -> bool:
    """
    Проверяет, инициализирована ли база данных и открыто ли соединение.
    
    Returns:
        bool: True если БД инициализирована и соединение открыто, False в противном случае
    """
    return _database is not None and not _database.is_closed()


def get_database_instance() -> Optional[SqliteDatabase]:
    """
    Возвращает текущий экземпляр базы данных без создания нового.
    
    Returns:
        Optional[SqliteDatabase]: Экземпляр БД или None если не инициализирована
    """
    return _database


@contextmanager
def database_connection():
    """
    Контекстный менеджер для работы с базой данных.
    Обеспечивает автоматическое управление соединением.
    
    Использование:
        with database_connection() as db:
            # Работа с БД
            User.create(...)
    
    Yields:
        SqliteDatabase: Экземпляр базы данных
    """
    db = get_database()
    
    try:
        # Убеждаемся, что соединение открыто
        if db.is_closed():
            db.connect(reuse_if_open=True)
        
        yield db
        
    except Exception as e:
        logger.error(f"Ошибка при работе с БД через контекстный менеджер: {e}", exc_info=True)
        raise
    finally:
        # Для SQLite обычно не нужно закрывать соединение после каждого использования,
        # так как используется singleton. Но можно добавить логику при необходимости.
        pass


def reconnect_database():
    """
    Переподключается к базе данных.
    Полезно при ошибках соединения.
    
    Returns:
        SqliteDatabase: Экземпляр базы данных
    """
    global _database
    
    with _database_lock:
        if _database is not None:
            try:
                if not _database.is_closed():
                    _database.close()
            except Exception:
                pass
            _database = None
        
        logger.info("Переподключение к базе данных...")
        return get_database()
