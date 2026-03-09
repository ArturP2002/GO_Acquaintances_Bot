"""
Репозиторий для работы с настройками.
Слой доступа к данным для модели Settings.
"""
from typing import Optional
from datetime import datetime

from database.models.settings import Settings
from core.cache import get_cached_setting, set_cached_setting


class SettingsRepository:
    """Репозиторий для работы с настройками."""
    
    @staticmethod
    def get(key: str) -> Optional[str]:
        """
        Получает значение настройки по ключу.
        Использует кэширование для оптимизации (TTL 5 минут).
        
        Args:
            key: Ключ настройки
            
        Returns:
            Значение настройки или None если не найдена
        """
        # Проверяем кэш
        cached_value = get_cached_setting(key)
        if cached_value is not None:
            return cached_value
        
        # Получаем из БД
        try:
            setting = Settings.get(Settings.key == key)
            value = setting.value
            
            # Кэшируем результат на 5 минут
            set_cached_setting(key, value, ttl=300)
            
            return value
        except Settings.DoesNotExist:
            return None
    
    @staticmethod
    def get_int(key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Получает значение настройки как целое число.
        
        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если настройка не найдена
            
        Returns:
            Значение настройки как int или default
        """
        value = SettingsRepository.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_float(key: str, default: Optional[float] = None) -> Optional[float]:
        """
        Получает значение настройки как число с плавающей точкой.
        
        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если настройка не найдена
            
        Returns:
            Значение настройки как float или default
        """
        value = SettingsRepository.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_bool(key: str, default: Optional[bool] = None) -> Optional[bool]:
        """
        Получает значение настройки как булево значение.
        
        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если настройка не найдена
            
        Returns:
            Значение настройки как bool или default
        """
        value = SettingsRepository.get(key)
        if value is None:
            return default
        
        # Преобразуем строку в bool
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower_value = value.lower()
            if lower_value in ('true', '1', 'yes', 'on'):
                return True
            if lower_value in ('false', '0', 'no', 'off'):
                return False
        return default
    
    @staticmethod
    def set(key: str, value: str) -> Settings:
        """
        Устанавливает значение настройки.
        Создает настройку, если она не существует, или обновляет существующую.
        
        Args:
            key: Ключ настройки
            value: Значение настройки (будет преобразовано в строку)
            
        Returns:
            Созданный или обновленный объект Settings
        """
        # Преобразуем value в строку
        str_value = str(value)
        
        # Используем get_or_create для атомарной операции
        setting, created = Settings.get_or_create(
            key=key,
            defaults={'value': str_value}
        )
        
        if not created:
            # Обновляем существующую настройку
            setting.value = str_value
            setting.updated_at = datetime.now()
            setting.save()
        
        # Обновляем кэш
        set_cached_setting(key, str_value, ttl=300)
        
        return setting
    
    @staticmethod
    def set_int(key: str, value: int) -> Settings:
        """
        Устанавливает значение настройки как целое число.
        
        Args:
            key: Ключ настройки
            value: Значение настройки (int)
            
        Returns:
            Созданный или обновленный объект Settings
        """
        return SettingsRepository.set(key, str(value))
    
    @staticmethod
    def set_float(key: str, value: float) -> Settings:
        """
        Устанавливает значение настройки как число с плавающей точкой.
        
        Args:
            key: Ключ настройки
            value: Значение настройки (float)
            
        Returns:
            Созданный или обновленный объект Settings
        """
        return SettingsRepository.set(key, str(value))
    
    @staticmethod
    def set_bool(key: str, value: bool) -> Settings:
        """
        Устанавливает значение настройки как булево значение.
        
        Args:
            key: Ключ настройки
            value: Значение настройки (bool)
            
        Returns:
            Созданный или обновленный объект Settings
        """
        return SettingsRepository.set(key, 'true' if value else 'false')
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Удаляет настройку.
        
        Args:
            key: Ключ настройки
            
        Returns:
            True если настройка удалена, False если не найдена
        """
        try:
            setting = Settings.get(Settings.key == key)
            setting.delete_instance()
            return True
        except Settings.DoesNotExist:
            return False
    
    @staticmethod
    def exists(key: str) -> bool:
        """
        Проверяет существование настройки.
        
        Args:
            key: Ключ настройки
            
        Returns:
            True если настройка существует, False в противном случае
        """
        return Settings.select().where(Settings.key == key).exists()
    
    @staticmethod
    def get_all() -> list[Settings]:
        """
        Получает все настройки.
        
        Returns:
            Список всех настроек
        """
        return list(Settings.select().order_by(Settings.key))
