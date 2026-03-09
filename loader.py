"""
Загрузчик зависимостей для бота знакомств.
Инициализирует бота, диспетчер, базу данных и планировщик задач.
"""
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from peewee import SqliteDatabase

from config import config

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные экземпляры
bot: Optional[Bot] = None
dispatcher: Optional[Dispatcher] = None
database: Optional[SqliteDatabase] = None
scheduler: Optional[AsyncIOScheduler] = None


def init_bot() -> Bot:
    """
    Инициализирует экземпляр бота Telegram.
    
    Returns:
        Bot: Экземпляр бота aiogram
    """
    global bot
    
    if bot is not None:
        logger.warning("Бот уже инициализирован")
        return bot
    
    logger.info("Инициализация бота...")
    
    # Создание сессии для HTTP запросов
    session = AiohttpSession()
    
    # Создание экземпляра бота
    bot = Bot(
        token=config.BOT_TOKEN,
        session=session
    )
    
    logger.info("Бот успешно инициализирован")
    return bot


def init_dispatcher() -> Dispatcher:
    """
    Инициализирует диспетчер для обработки обновлений.
    
    Returns:
        Dispatcher: Экземпляр диспетчера aiogram
    """
    global dispatcher
    
    if dispatcher is not None:
        logger.warning("Диспетчер уже инициализирован")
        return dispatcher
    
    logger.info("Инициализация диспетчера...")
    
    # Создание диспетчера
    dispatcher = Dispatcher()
    
    logger.info("Диспетчер успешно инициализирован")
    return dispatcher


def init_database() -> SqliteDatabase:
    """
    Инициализирует подключение к базе данных SQLite.
    
    Returns:
        SqliteDatabase: Экземпляр базы данных Peewee
    """
    global database
    
    if database is not None:
        logger.warning("База данных уже инициализирована")
        return database
    
    # Преобразуем относительный путь в абсолютный относительно корня проекта
    db_path = config.DATABASE_PATH
    if not os.path.isabs(db_path):
        # Получаем корень проекта (1 уровень вверх от loader.py)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        db_path = os.path.join(project_root, db_path)
    
    logger.info(f"Инициализация базы данных: {db_path}")
    
    # Создание подключения к SQLite
    database = SqliteDatabase(
        db_path,
        pragmas={
            'journal_mode': 'delete',  # Обычный режим журналирования (без WAL для лучшей синхронизации)
            'foreign_keys': 1,      # Включение внешних ключей
            'ignore_check_constraints': 0
        }
    )
    
    logger.info("База данных успешно инициализирована")
    return database


def init_scheduler() -> AsyncIOScheduler:
    """
    Инициализирует планировщик задач APScheduler.
    
    Returns:
        AsyncIOScheduler: Экземпляр планировщика
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Планировщик уже инициализирован")
        return scheduler
    
    logger.info("Инициализация планировщика задач...")
    
    # Создание планировщика с асинхронным выполнением
    scheduler = AsyncIOScheduler()
    
    logger.info("Планировщик успешно инициализирован")
    return scheduler


def setup_scheduled_tasks(scheduler_instance: AsyncIOScheduler):
    """
    Настраивает все периодические задачи в планировщике.
    
    Args:
        scheduler_instance: Экземпляр планировщика APScheduler
    """
    logger.info("Настройка периодических задач...")
    
    # Импорт задач
    from tasks.reset_likes import reset_likes_task
    from tasks.send_referral_reminders import send_referral_reminders_task
    from tasks.cleanup_moderation_queue import cleanup_moderation_queue_task
    from tasks.profile_boost_rotation import profile_boost_rotation_task
    from tasks.freeze_inactive_profiles import freeze_inactive_profiles_task
    from services.notification_service import NotificationService
    from loader import get_bot
    
    # Ежедневная очистка старых данных (в 00:00 UTC)
    scheduler_instance.add_job(
        reset_likes_task,
        'cron',
        hour=0,
        minute=0,
        id='reset_likes_daily',
        replace_existing=True
    )
    logger.info("Задача очистки старых данных настроена (ежедневно в 00:00)")
    
    # Ежедневная очистка истекших бустов (в 01:00 UTC)
    scheduler_instance.add_job(
        profile_boost_rotation_task,
        'cron',
        hour=1,
        minute=0,
        id='cleanup_expired_boosts',
        replace_existing=True
    )
    logger.info("Задача очистки истекших бустов настроена (ежедневно в 01:00)")
    
    # Ежедневная очистка очереди модерации (в 02:00 UTC)
    scheduler_instance.add_job(
        cleanup_moderation_queue_task,
        'cron',
        hour=2,
        minute=0,
        id='cleanup_moderation_queue',
        replace_existing=True
    )
    logger.info("Задача очистки очереди модерации настроена (ежедневно в 02:00)")
    
    # Отправка напоминаний о рефералах (каждые 2 часа)
    scheduler_instance.add_job(
        send_referral_reminders_task,
        'interval',
        hours=2,
        id='send_referral_reminders',
        replace_existing=True
    )
    logger.info("Задача отправки напоминаний о рефералах настроена (каждые 2 часа)")
    
    # Уведомления неактивным пользователям (ежедневно в 10:00 UTC)
    async def notify_inactive_task():
        try:
            bot = get_bot()
            notification_service = NotificationService(bot)
            await notification_service.notify_inactive_users()
        except Exception as e:
            logger.error(f"Ошибка в задаче уведомления неактивных пользователей: {e}", exc_info=True)
    
    scheduler_instance.add_job(
        notify_inactive_task,
        'cron',
        hour=10,
        minute=0,
        id='notify_inactive_users',
        replace_existing=True
    )
    logger.info("Задача уведомления неактивных пользователей настроена (ежедневно в 10:00)")
    
    # Очистка истекших записей кэша (каждый час)
    from core.cache import CacheService
    async def cleanup_cache_task():
        try:
            deleted_count = CacheService.cleanup_expired()
            if deleted_count > 0:
                logger.debug(f"Очищено {deleted_count} истекших записей из кэша")
        except Exception as e:
            logger.error(f"Ошибка в задаче очистки кэша: {e}", exc_info=True)
    
    scheduler_instance.add_job(
        cleanup_cache_task,
        'interval',
        hours=1,
        id='cleanup_cache',
        replace_existing=True
    )
    logger.info("Задача очистки кэша настроена (каждый час)")
    
    # Заморозка неактивных анкет - ежедневно в 03:00 UTC
    scheduler_instance.add_job(
        freeze_inactive_profiles_task,
        'cron',
        hour=3,
        minute=0,
        id='freeze_inactive_profiles',
        replace_existing=True
    )
    logger.info("Задача заморозки неактивных анкет настроена (ежедневно в 03:00)")
    
    logger.info("Все периодические задачи успешно настроены")


async def init_all() -> tuple[Bot, Dispatcher, SqliteDatabase, AsyncIOScheduler]:
    """
    Инициализирует все компоненты системы.
    
    Returns:
        tuple: Кортеж из (bot, dispatcher, database, scheduler)
    """
    logger.info("Начало инициализации всех компонентов...")
    
    # Инициализация всех компонентов
    bot_instance = init_bot()
    dispatcher_instance = init_dispatcher()
    database_instance = init_database()
    scheduler_instance = init_scheduler()
    
    # Настройка периодических задач
    setup_scheduled_tasks(scheduler_instance)
    
    logger.info("Все компоненты успешно инициализированы")
    
    return bot_instance, dispatcher_instance, database_instance, scheduler_instance


async def close_all():
    """
    Закрывает все соединения и останавливает компоненты.
    """
    global bot, dispatcher, database, scheduler
    
    logger.info("Закрытие всех соединений...")
    
    # Остановка планировщика
    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен")
    
    # Закрытие базы данных
    if database is not None and not database.is_closed():
        database.close()
        logger.info("База данных закрыта")
    
    # Закрытие сессии бота
    if bot is not None:
        session = bot.session
        if hasattr(session, 'close'):
            await session.close()
        logger.info("Сессия бота закрыта")
    
    logger.info("Все соединения закрыты")


def get_bot() -> Bot:
    """
    Возвращает экземпляр бота.
    
    Returns:
        Bot: Экземпляр бота
        
    Raises:
        RuntimeError: Если бот не инициализирован
    """
    if bot is None:
        raise RuntimeError("Бот не инициализирован. Вызовите init_bot() или init_all()")
    return bot


def get_dispatcher() -> Dispatcher:
    """
    Возвращает экземпляр диспетчера.
    
    Returns:
        Dispatcher: Экземпляр диспетчера
        
    Raises:
        RuntimeError: Если диспетчер не инициализирован
    """
    if dispatcher is None:
        raise RuntimeError("Диспетчер не инициализирован. Вызовите init_dispatcher() или init_all()")
    return dispatcher


def get_database() -> SqliteDatabase:
    """
    Возвращает экземпляр базы данных.
    
    Returns:
        SqliteDatabase: Экземпляр базы данных
        
    Raises:
        RuntimeError: Если база данных не инициализирована
    """
    if database is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() или init_all()")
    return database


def get_scheduler() -> AsyncIOScheduler:
    """
    Возвращает экземпляр планировщика.
    
    Returns:
        AsyncIOScheduler: Экземпляр планировщика
        
    Raises:
        RuntimeError: Если планировщик не инициализирован
    """
    if scheduler is None:
        raise RuntimeError("Планировщик не инициализирован. Вызовите init_scheduler() или init_all()")
    return scheduler
