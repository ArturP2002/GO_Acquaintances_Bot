"""
Конфигурация бота знакомств.
Настройки загружаются из переменных окружения через .env файл.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Попытка импортировать BaseSettings из pydantic (v1) или pydantic_settings (v2)
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    try:
        from pydantic import BaseSettings, Field
    except ImportError:
        # Fallback: используем простой класс без pydantic
        BaseSettings = None
        Field = None


if BaseSettings is not None:
    class Settings(BaseSettings):
        """Настройки приложения."""
        
        # Telegram Bot
        BOT_TOKEN: str = Field(..., env="BOT_TOKEN", description="Токен Telegram бота")
        
        # Модерация
        MODERATION_GROUP_ID: int = Field(..., env="MODERATION_GROUP_ID", description="ID группы для модерации")
        ADMIN_GROUP_ID: Optional[int] = Field(None, env="ADMIN_GROUP_ID", description="ID группы для админов/жалоб")
        
        # AI модерация
        OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY", description="API ключ OpenAI для AI модерации")
        AI_MODEL: str = Field("gpt-4o-mini", env="AI_MODEL", description="Модель OpenAI для AI модерации")
        
        # Replicate API
        REPLICATE_API_KEY: Optional[str] = Field(None, env="REPLICATE_API_KEY", description="API ключ Replicate для генерации изображений")
        
        # Лимиты и настройки
        MAX_LIKES_PER_DAY: int = Field(50, env="MAX_LIKES_PER_DAY", description="Максимальное количество лайков в день")
        MIN_AGE: int = Field(16, env="MIN_AGE", description="Минимальный возраст для регистрации")
        BOOST_FREQUENCY: int = Field(15, env="BOOST_FREQUENCY", description="Частота показа буст-анкет (каждые N анкет)")
        REFERRAL_BONUS: int = Field(10, env="REFERRAL_BONUS", description="Бонус за реферала (boost_value)")
        
        # База данных
        DATABASE_PATH: str = Field("dating_bot.db", env="DATABASE_PATH", description="Путь к файлу базы данных SQLite")
        
        # Логирование
        LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL", description="Уровень логирования (DEBUG, INFO, WARNING, ERROR)")
        LOG_FILE: Optional[str] = Field(None, env="LOG_FILE", description="Путь к файлу логов (если None - только консоль)")
        
        # Инициализация owner
        OWNER_TELEGRAM_ID: Optional[int] = Field(None, env="OWNER_TELEGRAM_ID", description="Telegram ID первого owner (создается автоматически при запуске)")
        
        # Mini App
        MINI_APP_URL: Optional[str] = Field("https://b723-37-27-91-108.ngrok-free.app", env="MINI_APP_URL", description="URL для Mini App админ-панели")

        # Юридические документы (для сообщения при первом /start)
        TERMS_URL: Optional[str] = Field(None, env="TERMS_URL", description="URL пользовательского соглашения")
        PRIVACY_URL: Optional[str] = Field(None, env="PRIVACY_URL", description="URL политики конфиденциальности")
        
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True
else:
    # Fallback: простой класс без pydantic
    class Settings:
        """Настройки приложения."""
        
        def __init__(self):
            # Telegram Bot
            self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
            if not self.BOT_TOKEN:
                raise ValueError("BOT_TOKEN не установлен в переменных окружения")
            
            # Модерация
            mod_group_id = os.getenv("MODERATION_GROUP_ID", "")
            if not mod_group_id:
                raise ValueError("MODERATION_GROUP_ID не установлен в переменных окружения")
            self.MODERATION_GROUP_ID = int(mod_group_id)
            
            admin_group_id = os.getenv("ADMIN_GROUP_ID", "")
            self.ADMIN_GROUP_ID = int(admin_group_id) if admin_group_id else None
            
            # AI модерация
            self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or None
            self.AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
            
            # Replicate API
            self.REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY") or None
            
            # Лимиты и настройки
            self.MAX_LIKES_PER_DAY = int(os.getenv("MAX_LIKES_PER_DAY", "50"))
            self.MIN_AGE = int(os.getenv("MIN_AGE", "16"))
            self.BOOST_FREQUENCY = int(os.getenv("BOOST_FREQUENCY", "15"))
            self.REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "10"))
            
            # База данных
            self.DATABASE_PATH = os.getenv("DATABASE_PATH", "dating_bot.db")
            
            # Логирование
            self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
            self.LOG_FILE = os.getenv("LOG_FILE") or None
            
            # Инициализация owner
            owner_id = os.getenv("OWNER_TELEGRAM_ID", "")
            self.OWNER_TELEGRAM_ID = int(owner_id) if owner_id else None
            
            # Mini App
            # По умолчанию для локальной разработки
            self.MINI_APP_URL = os.getenv("MINI_APP_URL") or "https://b723-37-27-91-108.ngrok-free.app"

            # Юридические документы (для сообщения при первом /start)
            self.TERMS_URL = os.getenv("TERMS_URL")
            self.PRIVACY_URL = os.getenv("PRIVACY_URL")


# Создание глобального экземпляра настроек
config = Settings()
