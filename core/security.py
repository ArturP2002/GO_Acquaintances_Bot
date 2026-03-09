"""
Модуль безопасности для бота знакомств.
Содержит функции для проверки безопасности, валидации данных и защиты от атак.
"""
import hashlib
import hmac
import logging
import re
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Кэш для отслеживания попыток входа (в реальном приложении лучше использовать Redis)
_login_attempts: Dict[str, Dict[str, Any]] = {}


def validate_age(age: int, min_age: int = 16) -> bool:
    """
    Проверяет валидность возраста пользователя.
    
    Args:
        age: Возраст для проверки
        min_age: Минимальный допустимый возраст (по умолчанию 16)
        
    Returns:
        bool: True если возраст валиден, False в противном случае
    """
    if not isinstance(age, int):
        return False
    
    if age < min_age:
        logger.warning(f"Попытка регистрации с возрастом {age} (минимум {min_age})")
        return False
    
    if age > 120:  # Разумный максимум
        logger.warning(f"Попытка регистрации с подозрительным возрастом {age}")
        return False
    
    return True


def validate_username(username: Optional[str]) -> bool:
    """
    Проверяет валидность username Telegram.
    
    Args:
        username: Username для проверки
        
    Returns:
        bool: True если username валиден, False в противном случае
    """
    if username is None:
        return True  # Username не обязателен в Telegram
    
    if not isinstance(username, str):
        return False
    
    # Telegram username: 5-32 символа, буквы, цифры, подчеркивания
    pattern = r'^[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, username))


def validate_telegram_id(telegram_id: int) -> bool:
    """
    Проверяет валидность Telegram ID.
    
    Args:
        telegram_id: Telegram ID для проверки
        
    Returns:
        bool: True если ID валиден, False в противном случае
    """
    if not isinstance(telegram_id, int):
        return False
    
    # Telegram ID должен быть положительным числом
    if telegram_id <= 0:
        return False
    
    # Разумный максимум (Telegram ID обычно до 2^63-1)
    if telegram_id > 2**63 - 1:
        return False
    
    return True


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """
    Очищает текст от потенциально опасных символов и обрезает до максимальной длины.
    
    Args:
        text: Текст для очистки
        max_length: Максимальная длина текста
        
    Returns:
        str: Очищенный текст
    """
    if not isinstance(text, str):
        return ""
    
    # Удаление управляющих символов (кроме переносов строк)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Обрезка до максимальной длины
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def hash_data(data: str, salt: Optional[str] = None) -> str:
    """
    Хэширует данные с использованием SHA-256.
    
    Args:
        data: Данные для хэширования
        salt: Опциональная соль для дополнительной безопасности
        
    Returns:
        str: Хэш данных в hex формате
    """
    if salt:
        data = f"{data}{salt}"
    
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def verify_hmac(data: str, signature: str, secret: str) -> bool:
    """
    Проверяет HMAC подпись данных.
    
    Args:
        data: Данные для проверки
        signature: Подпись для проверки
        secret: Секретный ключ
        
    Returns:
        bool: True если подпись валидна, False в противном случае
    """
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Ошибка при проверке HMAC: {e}")
        return False


def check_login_attempts(identifier: str, max_attempts: int = 5, lockout_time: int = 300) -> tuple[bool, Optional[int]]:
    """
    Проверяет количество попыток входа и блокировку.
    
    Args:
        identifier: Идентификатор пользователя (telegram_id или IP)
        max_attempts: Максимальное количество попыток
        lockout_time: Время блокировки в секундах
        
    Returns:
        tuple: (разрешено ли, оставшееся время блокировки в секундах или None)
    """
    current_time = time.time()
    
    if identifier not in _login_attempts:
        return True, None
    
    attempts_data = _login_attempts[identifier]
    
    # Проверка блокировки
    if attempts_data.get('locked_until', 0) > current_time:
        remaining = int(attempts_data['locked_until'] - current_time)
        return False, remaining
    
    # Если блокировка истекла, сброс попыток
    if attempts_data.get('locked_until', 0) <= current_time:
        del _login_attempts[identifier]
        return True, None
    
    # Проверка количества попыток
    if attempts_data.get('count', 0) >= max_attempts:
        # Установка блокировки
        attempts_data['locked_until'] = current_time + lockout_time
        return False, lockout_time
    
    return True, None


def record_login_attempt(identifier: str, success: bool):
    """
    Записывает попытку входа.
    
    Args:
        identifier: Идентификатор пользователя
        success: Успешна ли попытка входа
    """
    if success:
        # При успешном входе сброс счетчика
        if identifier in _login_attempts:
            del _login_attempts[identifier]
    else:
        # При неуспешном входе увеличение счетчика
        if identifier not in _login_attempts:
            _login_attempts[identifier] = {'count': 0, 'last_attempt': time.time()}
        
        _login_attempts[identifier]['count'] += 1
        _login_attempts[identifier]['last_attempt'] = time.time()


def is_suspicious_activity(telegram_id: int, activity_type: str, threshold: int = 10) -> bool:
    """
    Проверяет подозрительную активность пользователя.
    
    Args:
        telegram_id: Telegram ID пользователя
        activity_type: Тип активности (например, 'likes', 'reports')
        threshold: Порог для определения подозрительности
        
    Returns:
        bool: True если активность подозрительна, False в противном случае
    """
    # В реальном приложении здесь должна быть проверка в БД
    # Например, количество действий за последний час
    # Это упрощенная версия для демонстрации
    
    identifier = f"{telegram_id}_{activity_type}"
    
    if identifier not in _login_attempts:
        _login_attempts[identifier] = {'count': 0, 'timestamp': time.time()}
    
    attempts_data = _login_attempts[identifier]
    
    # Сброс счетчика если прошло больше часа
    if time.time() - attempts_data.get('timestamp', 0) > 3600:
        attempts_data['count'] = 0
        attempts_data['timestamp'] = time.time()
    
    attempts_data['count'] += 1
    
    if attempts_data['count'] > threshold:
        logger.warning(f"Подозрительная активность: {activity_type} для пользователя {telegram_id}")
        return True
    
    return False


def generate_secure_token(length: int = 32) -> str:
    """
    Генерирует безопасный случайный токен.
    
    Args:
        length: Длина токена в байтах
        
    Returns:
        str: Случайный токен в hex формате
    """
    import secrets
    return secrets.token_hex(length)


def validate_referral_code(code: str) -> bool:
    """
    Проверяет валидность реферального кода.
    
    Args:
        code: Реферальный код для проверки
        
    Returns:
        bool: True если код валиден, False в противном случае
    """
    if not isinstance(code, str):
        return False
    
    # Реферальный код: префикс "ref_" + цифры/буквы
    pattern = r'^ref_[a-zA-Z0-9]{5,20}$'
    return bool(re.match(pattern, code))


def clean_login_attempts_cache():
    """
    Очищает кэш попыток входа от устаревших записей.
    Должна вызываться периодически (например, через планировщик).
    """
    current_time = time.time()
    expired_keys = [
        key for key, data in _login_attempts.items()
        if data.get('locked_until', 0) < current_time and data.get('count', 0) == 0
    ]
    
    for key in expired_keys:
        del _login_attempts[key]
    
    if expired_keys:
        logger.debug(f"Очищено {len(expired_keys)} устаревших записей из кэша попыток входа")
