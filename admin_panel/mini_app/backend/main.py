"""
FastAPI приложение для админ-панели Telegram бота знакомств.
Предоставляет REST API для управления пользователями, жалобами, настройками и бустами.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from admin_panel.mini_app.backend.routers import users, complaints, settings, boost, stats
from admin_panel.mini_app.backend.routers.settings import test_profiles_router

# Импорт моделей для инициализации БД
from database.models import (
    User, Profile, ProfileMedia, Like, ProfileView, ProfileHistory,
    Match, Complaint, ComplaintAction, ModerationQueue, ModerationAction,
    Referral, Boost, Settings, AdminUser
)

logger = logging.getLogger(__name__)


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
            Referral, Boost, Settings, AdminUser
        ]
        
        # Создаем таблицы (safe=True предотвращает ошибки, если таблицы уже существуют)
        database.create_tables(tables, safe=True)
        logger.info("Таблицы базы данных успешно инициализированы")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации таблиц БД: {e}", exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Инициализация при запуске
    logger.info("Инициализация админ-панели...")
    
    # Подключение к БД (синхронный вызов)
    from core.database import init_database
    db = init_database()
    
    # Убеждаемся, что соединение открыто
    if db.is_closed():
        try:
            db.connect(reuse_if_open=True)
            logger.info("База данных подключена")
        except Exception as e:
            logger.error(f"Ошибка при подключении к БД: {e}", exc_info=True)
            raise
    else:
        logger.info("База данных уже подключена")
    
    # Инициализация таблиц базы данных
    try:
        init_database_tables(db)
        logger.info("✅ Таблицы базы данных для Mini App инициализированы")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при инициализации таблиц БД: {e}", exc_info=True)
        # Прерываем запуск, так как без таблиц приложение не сможет работать
        raise
    
    # Инициализация первого owner (если указан в конфиге и owner еще не существует)
    try:
        from utils.init_owner import init_owner_if_needed
        from config import config
        owner_initialized = init_owner_if_needed(config.OWNER_TELEGRAM_ID)
        if owner_initialized:
            logger.info("✅ Owner инициализирован для Mini App")
        else:
            logger.debug("Owner не был инициализирован (OWNER_TELEGRAM_ID не указан или уже существует)")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при инициализации owner: {e}", exc_info=True)
        # Не прерываем запуск, так как owner может быть создан вручную или через основной бот
    
    yield
    
    # Очистка при остановке
    logger.info("Остановка админ-панели...")
    # Не закрываем БД, так как она используется и в основном боте


# Создание FastAPI приложения
app = FastAPI(
    title="Admin Panel API",
    description="REST API для админ-панели Telegram бота знакомств",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для проверки подключения к БД перед каждым запросом
@app.middleware("http")
async def db_check_middleware(request: Request, call_next):
    """Middleware для проверки подключения к БД перед каждым запросом."""
    from core.database import get_database
    
    try:
        db = get_database()
        if db.is_closed():
            db.connect(reuse_if_open=True)
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения к БД: {e}", exc_info=True)
        # Продолжаем выполнение, но запрос может упасть, если БД недоступна
    
    # Логирование запросов для отладки
    logger.debug(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
    except Exception as e:
        logger.error(f"Необработанная ошибка в middleware: {e}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Внутренняя ошибка сервера: {str(e)}"}
        )


# Глобальный обработчик исключений HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений."""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Глобальный обработчик всех остальных исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик всех необработанных исключений."""
    logger.error(
        f"Необработанное исключение: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "query_params": str(request.query_params)
        }
    )
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": f"Внутренняя ошибка сервера: {str(exc)}"}
    )

# Подключение роутеров
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(complaints.router, prefix="/api/complaints", tags=["complaints"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(test_profiles_router, prefix="/api/test-profiles", tags=["test-profiles"])
app.include_router(boost.router, prefix="/api/boost", tags=["boost"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


@app.get("/")
async def root():
    """Корневой endpoint для проверки работы API."""
    return {"message": "Admin Panel API", "status": "running"}


@app.get("/health")
async def health_check():
    """Проверка здоровья API."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
