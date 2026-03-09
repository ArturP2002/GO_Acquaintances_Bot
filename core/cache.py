"""
Модуль кэширования для оптимизации производительности.
Поддерживает in-memory кэш и подготовку к Redis для масштабирования.
"""
import logging
import time
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory кэш (для начала, позже можно заменить на Redis)
_cache: Dict[str, Dict[str, Any]] = {}


class CacheService:
    """Сервис для кэширования данных."""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Optional[Any]:
        """
        Получает значение из кэша.
        
        Args:
            key: Ключ кэша
            default: Значение по умолчанию если ключ не найден
            
        Returns:
            Значение из кэша или default
        """
        if key not in _cache:
            return default
        
        cache_entry = _cache[key]
        
        # Проверка истечения срока действия
        if cache_entry.get('expires_at') and datetime.now() > cache_entry['expires_at']:
            del _cache[key]
            return default
        
        return cache_entry.get('value', default)
    
    @staticmethod
    def set(key: str, value: Any, ttl_seconds: int = 30) -> None:
        """
        Устанавливает значение в кэш с TTL.
        
        Args:
            key: Ключ кэша
            value: Значение для кэширования
            ttl_seconds: Время жизни в секундах (по умолчанию 30)
        """
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        _cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.now()
        }
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Удаляет значение из кэша.
        
        Args:
            key: Ключ кэша
            
        Returns:
            True если ключ был удален, False если не найден
        """
        if key in _cache:
            del _cache[key]
            return True
        return False
    
    @staticmethod
    def clear() -> None:
        """Очищает весь кэш."""
        global _cache
        _cache.clear()
    
    @staticmethod
    def cleanup_expired() -> int:
        """
        Очищает истекшие записи из кэша.
        
        Returns:
            Количество удаленных записей
        """
        now = datetime.now()
        expired_keys = [
            key for key, entry in _cache.items()
            if entry.get('expires_at') and entry['expires_at'] < now
        ]
        
        for key in expired_keys:
            del _cache[key]
        
        if expired_keys:
            logger.debug(f"Очищено {len(expired_keys)} истекших записей из кэша")
        
        return len(expired_keys)


# Специализированные функции кэширования для разных типов данных

def cache_candidates_key(user_id: int, min_age: int, max_age: int) -> str:
    """Генерирует ключ кэша для кандидатов."""
    return f"candidates:{user_id}:{min_age}:{max_age}"


def cache_settings_key(key: str) -> str:
    """Генерирует ключ кэша для настроек."""
    return f"settings:{key}"


def cache_boost_key(user_id: int) -> str:
    """Генерирует ключ кэша для boost значения."""
    return f"boost:{user_id}"


def get_cached_candidates(user_id: int, min_age: int, max_age: int) -> Optional[list]:
    """
    Получает кандидатов из кэша.
    
    Args:
        user_id: ID пользователя
        min_age: Минимальный возраст
        max_age: Максимальный возраст
        
    Returns:
        Список кандидатов или None
    """
    key = cache_candidates_key(user_id, min_age, max_age)
    return CacheService.get(key)


def set_cached_candidates(user_id: int, min_age: int, max_age: int, candidates: list, ttl: int = 30) -> None:
    """
    Кэширует кандидатов.
    
    Args:
        user_id: ID пользователя
        min_age: Минимальный возраст
        max_age: Максимальный возраст
        candidates: Список кандидатов
        ttl: Время жизни в секундах (по умолчанию 30)
    """
    key = cache_candidates_key(user_id, min_age, max_age)
    CacheService.set(key, candidates, ttl)


def get_cached_setting(key: str) -> Optional[str]:
    """
    Получает настройку из кэша.
    
    Args:
        key: Ключ настройки
        
    Returns:
        Значение настройки или None
    """
    cache_key = cache_settings_key(key)
    return CacheService.get(cache_key)  # Кэш настроек на 5 минут (TTL задается при set)


def set_cached_setting(key: str, value: str, ttl: int = 300) -> None:
    """
    Кэширует настройку.
    
    Args:
        key: Ключ настройки
        value: Значение настройки
        ttl: Время жизни в секундах (по умолчанию 300)
    """
    cache_key = cache_settings_key(key)
    CacheService.set(cache_key, value, ttl)


def get_cached_boost(user_id: int) -> Optional[int]:
    """
    Получает boost значение из кэша.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Boost значение или None
    """
    key = cache_boost_key(user_id)
    return CacheService.get(key)  # Кэш boost на 1 минуту (TTL задается при set)


def set_cached_boost(user_id: int, boost_value: int, ttl: int = 60) -> None:
    """
    Кэширует boost значение.
    
    Args:
        user_id: ID пользователя
        boost_value: Значение boost
        ttl: Время жизни в секундах (по умолчанию 60)
    """
    key = cache_boost_key(user_id)
    CacheService.set(key, boost_value, ttl)


def invalidate_user_cache(user_id: int) -> None:
    """
    Инвалидирует весь кэш пользователя.
    Вызывается при изменении данных пользователя (лайк, просмотр и т.д.).
    
    Args:
        user_id: ID пользователя
    """
    # Удаляем все ключи, связанные с пользователем
    keys_to_delete = [
        key for key in _cache.keys()
        if f":{user_id}:" in key or key.endswith(f":{user_id}")
    ]
    
    for key in keys_to_delete:
        CacheService.delete(key)
    
    if keys_to_delete:
        logger.debug(f"Инвалидирован кэш для пользователя {user_id}: {len(keys_to_delete)} записей")
