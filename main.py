"""
Точка входа для Telegram-бота знакомств.
Инициализирует все компоненты, подключает роутеры и запускает бота.
"""
import asyncio
import logging
import sys

from aiogram import Dispatcher
from aiogram.types import BotCommand

from config import config
from loader import init_all, close_all

# Импорт роутеров
from handlers.user import user_router
from handlers.moderation import moderation_router
from handlers.admin import admin_router

# Импорт моделей для инициализации БД
from database.models import (
    User, Profile, ProfileMedia, Like, ProfileView, ProfileHistory,
    Match, Complaint, ComplaintAction, ModerationQueue, ModerationAction,
    Referral, Boost, Settings, AdminUser,
    AdvertisementCampaign, AdvertisementMedia
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        *([logging.FileHandler(config.LOG_FILE)] if config.LOG_FILE else [])
    ]
)

logger = logging.getLogger(__name__)


async def setup_bot_commands(bot):
    """
    Устанавливает команды бота в меню Telegram.
    """
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


def init_database_tables(database):
    """
    Инициализирует базу данных, создавая все необходимые таблицы.
    
    Args:
        database: Экземпляр базы данных Peewee
    """
    logger.info("Инициализация таблиц базы данных...")
    
    try:
        # Подключаемся к базе данных, если еще не подключены
        if database.is_closed():
            database.connect()
        
        # Список всех моделей для создания таблиц
        tables = [
            User, Profile, ProfileMedia, Like, ProfileView, ProfileHistory,
            Match, Complaint, ComplaintAction, ModerationQueue, ModerationAction,
            Referral, Boost, Settings, AdminUser,
            AdvertisementCampaign, AdvertisementMedia
        ]
        
        # Создаем таблицы (safe=True предотвращает ошибки, если таблицы уже существуют)
        database.create_tables(tables, safe=True)
        
        # Миграции: добавляем отсутствующие колонки
        _apply_migrations(database)
        
        logger.info("Таблицы базы данных успешно инициализированы")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации таблиц БД: {e}", exc_info=True)
        raise


def _apply_migrations(database):
    """
    Применяет миграции для добавления отсутствующих колонок в существующие таблицы.
    
    Args:
        database: Экземпляр базы данных Peewee
    """
    logger.info("Применение миграций базы данных...")
    
    try:
        # Проверяем существование таблицы через прямой SQL запрос
        try:
            cursor = database.execute_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
            )
            table_exists = cursor.fetchone() is not None
            logger.debug(f"Таблица profiles существует (проверка через sqlite_master): {table_exists}")
        except Exception as e:
            logger.warning(f"Ошибка при проверке существования таблицы profiles: {e}")
            table_exists = False
        
        if not table_exists:
            logger.info("Таблица profiles еще не создана, миграция будет пропущена (таблица создастся со всеми полями модели)")
            return
        
        # Проверяем структуру таблицы (это также подтверждает, что таблица существует)
        try:
            cursor = database.execute_sql("PRAGMA table_info(profiles)")
            columns = [row[1] for row in cursor.fetchall()]
            logger.debug(f"Колонки в таблице profiles: {', '.join(columns)}")
        except Exception as e:
            logger.error(f"Ошибка при получении информации о колонках таблицы profiles: {e}", exc_info=True)
            # Если не можем получить информацию о колонках, значит таблицы нет или проблема с БД
            return
        
        # Проверяем наличие колонки filter_by_opposite_gender
        if 'filter_by_opposite_gender' not in columns:
            logger.info("⚠️ Колонка filter_by_opposite_gender отсутствует в таблице profiles. Добавление...")
            try:
                # Дополнительная проверка существования таблицы перед ALTER TABLE
                cursor = database.execute_sql(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
                )
                if cursor.fetchone() is None:
                    logger.warning("Таблица profiles исчезла между проверками, пропускаем миграцию")
                    return
                
                database.execute_sql(
                    "ALTER TABLE profiles ADD COLUMN filter_by_opposite_gender INTEGER DEFAULT 1"
                )
                logger.info("✅ Колонка filter_by_opposite_gender успешно добавлена в таблицу profiles")
                
                # Проверяем, что колонка действительно добавлена
                cursor = database.execute_sql("PRAGMA table_info(profiles)")
                columns_after = [row[1] for row in cursor.fetchall()]
                if 'filter_by_opposite_gender' in columns_after:
                    logger.info("✅ Подтверждено: колонка filter_by_opposite_gender успешно добавлена")
                else:
                    logger.error("❌ ОШИБКА: колонка filter_by_opposite_gender не была добавлена!")
                    
            except Exception as e:
                # Если колонка уже существует (race condition), это нормально
                error_msg = str(e).lower()
                if "duplicate column name" in error_msg or "already exists" in error_msg:
                    logger.info("Колонка filter_by_opposite_gender уже существует (возможно добавлена параллельно)")
                elif "no such table" in error_msg:
                    logger.warning("Таблица profiles не найдена при попытке добавления колонки. Возможно, таблица была удалена или еще не создана.")
                else:
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА при добавлении колонки filter_by_opposite_gender: {e}", exc_info=True)
                    # Это критическая ошибка, но не прерываем выполнение
        else:
            logger.info("✅ Колонка filter_by_opposite_gender уже существует в таблице profiles")
        
        # Миграция: проверяем и создаем таблицы для рекламных кампаний, если они отсутствуют
        try:
            # Проверяем существование таблицы advertisement_campaigns
            cursor = database.execute_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='advertisement_campaigns'"
            )
            campaigns_table_exists = cursor.fetchone() is not None
            
            if not campaigns_table_exists:
                logger.info("⚠️ Таблица advertisement_campaigns отсутствует. Создание...")
                AdvertisementCampaign.create_table(safe=True)
                logger.info("✅ Таблица advertisement_campaigns успешно создана")
            else:
                logger.debug("✅ Таблица advertisement_campaigns уже существует")
            
            # Проверяем существование таблицы advertisement_media
            cursor = database.execute_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='advertisement_media'"
            )
            media_table_exists = cursor.fetchone() is not None
            
            if not media_table_exists:
                logger.info("⚠️ Таблица advertisement_media отсутствует. Создание...")
                AdvertisementMedia.create_table(safe=True)
                logger.info("✅ Таблица advertisement_media успешно создана")
            else:
                logger.debug("✅ Таблица advertisement_media уже существует")
                
        except Exception as e:
            logger.error(f"❌ ОШИБКА при создании таблиц рекламных кампаний: {e}", exc_info=True)
            # Не прерываем выполнение, но логируем как ошибку
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА при применении миграций: {e}", exc_info=True)
        # Не прерываем выполнение, но логируем как ошибку


async def main():
    """
    Основная функция запуска бота.
    Инициализирует все компоненты, подключает роутеры и запускает polling.
    """
    try:
        logger.info("Запуск бота знакомств...")
        
        # Инициализация всех компонентов
        bot, dispatcher, database, scheduler = await init_all()
        
        # Инициализация таблиц базы данных
        init_database_tables(database)
        
        # Инициализация первого owner (если указан в конфиге и owner еще не существует)
        from utils.init_owner import init_owner_if_needed
        init_owner_if_needed(config.OWNER_TELEGRAM_ID)
        
        # Проверка и генерация тестовых анкет при необходимости
        try:
            from utils.generate_test_profiles import has_test_profiles, generate_test_profiles
            from database.repositories.settings_repo import SettingsRepository
            
            if not has_test_profiles():
                logger.info("Тестовые анкеты еще не были созданы. Запуск генерации 30 тестовых профилей...")
                
                # Устанавливаем флаг ДО генерации, чтобы даже при ошибках
                # тестовые профили не создавались повторно
                SettingsRepository.set_bool("test_profiles_initialized", True)
                logger.info("Флаг инициализации установлен - тестовые профили не будут создаваться повторно после удаления.")
                
                results = await generate_test_profiles(count=30, bot=bot)
                
                if results['success'] and results['created'] > 0:
                    logger.info(
                        f"✅ Успешно сгенерировано {results['created']} тестовых профилей. "
                        f"Ошибок: {len(results['errors'])}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Генерация тестовых профилей завершилась с проблемами. "
                        f"Создано: {results['created']}, Ошибок: {len(results['errors'])}"
                    )
                    if results['errors']:
                        for error in results['errors'][:5]:  # Показываем первые 5 ошибок
                            logger.warning(f"  - {error}")
            else:
                from utils.generate_test_profiles import get_test_profiles_count
                count = get_test_profiles_count()
                logger.info(
                    f"Тестовые профили уже были инициализированы ранее. "
                    f"Текущее количество тестовых профилей в БД: {count}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Не удалось проверить/сгенерировать тестовые анкеты: {e}", exc_info=True)
            logger.info("Бот продолжит работу без тестовых анкет")
        
        # Запуск mini app серверов (бэкенд и фронтенд)
        try:
            from admin_panel.mini_app.start_servers import start_backend, start_frontend
            backend_started = start_backend()
            frontend_started = start_frontend()
            
            if backend_started and frontend_started:
                logger.info("✅ Mini App серверы запущены (бэкенд: http://localhost:8000, фронтенд: http://localhost:3000)")
            elif backend_started:
                logger.warning("⚠️ Бэкенд mini app запущен, но фронтенд не запустился")
            else:
                logger.warning("⚠️ Mini App серверы не запущены. Проверьте зависимости.")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось запустить mini app серверы: {e}")
            logger.info("Бот продолжит работу без mini app")
        
        # Регистрация middleware
        from middlewares.database import DatabaseMiddleware
        from middlewares.user_context import UserContextMiddleware
        from middlewares.ban_check import BanCheckMiddleware
        from middlewares.verification_check import VerificationCheckMiddleware
        
        dispatcher.update.outer_middleware(DatabaseMiddleware(database))
        dispatcher.update.outer_middleware(UserContextMiddleware())
        dispatcher.update.outer_middleware(BanCheckMiddleware())
        dispatcher.update.outer_middleware(VerificationCheckMiddleware())
        logger.info("Middleware зарегистрированы")
        
        # Подключение роутеров
        dispatcher.include_router(user_router)
        dispatcher.include_router(moderation_router)
        dispatcher.include_router(admin_router)
        
        # Установка команд бота
        await setup_bot_commands(bot)
        
        # Запуск планировщика задач (если нужен)
        if scheduler and not scheduler.running:
            scheduler.start()
            logger.info("Планировщик задач запущен")
        
        logger.info("Бот успешно запущен и готов к работе")
        
        # Запуск polling (получение обновлений)
        await dispatcher.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)
        raise
    finally:
        # Остановка mini app серверов
        try:
            from admin_panel.mini_app.start_servers import stop_servers
            stop_servers()
        except Exception as e:
            logger.warning(f"Ошибка при остановке mini app серверов: {e}")
        
        # Закрытие всех соединений
        await close_all()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}", exc_info=True)
        sys.exit(1)
