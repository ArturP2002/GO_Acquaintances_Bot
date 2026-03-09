"""
Модуль для работы с планировщиком задач APScheduler.
Обеспечивает инициализацию и управление фоновыми задачами.
"""
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger(__name__)

# Глобальный экземпляр планировщика
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Возвращает экземпляр планировщика задач.
    Если планировщик еще не инициализирован, создает новый.
    
    Returns:
        AsyncIOScheduler: Экземпляр планировщика APScheduler
        
    Raises:
        RuntimeError: Если не удалось создать планировщик
    """
    global _scheduler
    
    if _scheduler is not None:
        return _scheduler
    
    logger.info("Создание планировщика задач...")
    
    try:
        # Настройка хранилища заданий (в памяти)
        jobstores = {
            'default': MemoryJobStore()
        }
        
        # Настройка исполнителя (асинхронный)
        executors = {
            'default': AsyncIOExecutor()
        }
        
        # Настройки планировщика
        job_defaults = {
            'coalesce': True,  # Объединять несколько пропущенных запусков в один
            'max_instances': 3,  # Максимальное количество одновременно выполняемых экземпляров задачи
            'misfire_grace_time': 30  # Время в секундах, в течение которого задача может быть выполнена после пропуска
        }
        
        # Создание планировщика
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        logger.info("Планировщик задач успешно создан")
        return _scheduler
        
    except Exception as e:
        logger.error(f"Ошибка при создании планировщика: {e}", exc_info=True)
        raise RuntimeError(f"Не удалось создать планировщик задач: {e}")


def init_scheduler() -> AsyncIOScheduler:
    """
    Инициализирует планировщик задач.
    Явно создает планировщик, если он еще не был создан.
    
    Returns:
        AsyncIOScheduler: Экземпляр планировщика
    """
    return get_scheduler()


def start_scheduler():
    """
    Запускает планировщик задач, если он еще не запущен.
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = get_scheduler()
    
    if not _scheduler.running:
        logger.info("Запуск планировщика задач...")
        _scheduler.start()
        logger.info("Планировщик задач запущен")
    else:
        logger.warning("Планировщик задач уже запущен")


def stop_scheduler():
    """
    Останавливает планировщик задач.
    """
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        logger.info("Остановка планировщика задач...")
        _scheduler.shutdown(wait=True)
        logger.info("Планировщик задач остановлен")


def is_scheduler_running() -> bool:
    """
    Проверяет, запущен ли планировщик задач.
    
    Returns:
        bool: True если планировщик запущен, False в противном случае
    """
    return _scheduler is not None and _scheduler.running


def get_scheduler_instance() -> Optional[AsyncIOScheduler]:
    """
    Возвращает текущий экземпляр планировщика без создания нового.
    
    Returns:
        Optional[AsyncIOScheduler]: Экземпляр планировщика или None если не инициализирован
    """
    return _scheduler
