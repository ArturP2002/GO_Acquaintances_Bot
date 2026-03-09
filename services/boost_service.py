"""
Сервис для работы с бустами анкет.
Управление бустами: создание, расчет приоритета, влияние на алгоритм выдачи.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

from database.repositories.boost_repo import BoostRepository
from database.models.boost import Boost
from core.constants import BoostType
from core.cache import get_cached_boost, set_cached_boost, invalidate_user_cache

# Настройка логирования
logger = logging.getLogger(__name__)


class BoostService:
    """Сервис для работы с бустами анкет."""
    
    @staticmethod
    def add_boost(user_id: int, boost_value: int, expires_at: Optional[datetime] = None) -> Boost:
        """
        Создает новый буст для пользователя.
        
        Бусты повышают приоритет показа анкеты в алгоритме выдачи.
        Значения boost_value:
        - 0 = обычный (без буста)
        - 1 = реферальный буст
        - 3 = платный буст
        
        Args:
            user_id: ID пользователя
            boost_value: Значение буста (0=обычный, 1=реферальный, 3=платный)
            expires_at: Дата и время истечения буста (опционально, None = бессрочный)
            
        Returns:
            Созданный объект Boost
            
        Raises:
            Exception: Если произошла ошибка при создании буста
        """
        try:
            boost = BoostRepository.create(
                user_id=user_id,
                boost_value=boost_value,
                expires_at=expires_at
            )
            logger.info(
                f"Создан буст для пользователя {user_id}: "
                f"boost_value={boost_value}, expires_at={expires_at}"
            )
            
            # Инвалидируем кэш boost для пользователя
            invalidate_user_cache(user_id)
            
            return boost
        except Exception as e:
            logger.error(
                f"Ошибка при создании буста для пользователя {user_id}: {e}",
                exc_info=True
            )
            raise
    
    @staticmethod
    def get_total_boost(user_id: int) -> int:
        """
        Вычисляет суммарное значение активных бустов пользователя.
        Использует кэширование для оптимизации (TTL 60 секунд).
        
        Активными считаются бусты, у которых expires_at > NOW() или expires_at = NULL.
        Сумма всех активных бустов используется в формуле score для алгоритма выдачи:
        score = boost * 50 + match_rate * 30 + activity_score * 10 + random(0, 5)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Суммарное значение активных бустов (0 если нет активных бустов)
        """
        try:
            # Проверяем кэш
            cached_boost = get_cached_boost(user_id)
            if cached_boost is not None:
                return cached_boost
            
            # Получаем из БД
            total_boost = BoostRepository.get_total_boost_value(user_id)
            
            # Кэшируем результат на 60 секунд
            set_cached_boost(user_id, total_boost, ttl=60)
            
            logger.debug(f"Суммарный boost для пользователя {user_id}: {total_boost}")
            return total_boost
        except Exception as e:
            logger.error(
                f"Ошибка при расчете boost для пользователя {user_id}: {e}",
                exc_info=True
            )
            return 0
    
    @staticmethod
    def calculate_priority(user_id: int) -> int:
        """
        Вычисляет приоритет пользователя на основе активных бустов.
        
        Это алиас для get_total_boost() для совместимости с планом.
        Приоритет = сумма активных бустов.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Приоритет пользователя (сумма активных бустов)
        """
        return BoostService.get_total_boost(user_id)
    
    @staticmethod
    def add_referral_boost(user_id: int, duration_days: Optional[int] = None) -> Boost:
        """
        Добавляет реферальный буст пользователю.
        
        Args:
            user_id: ID пользователя
            duration_days: Длительность буста в днях (None = бессрочный)
            
        Returns:
            Созданный объект Boost
        """
        expires_at = None
        if duration_days is not None:
            expires_at = datetime.now() + timedelta(days=duration_days)
        
        return BoostService.add_boost(
            user_id=user_id,
            boost_value=BoostType.REFERRAL,
            expires_at=expires_at
        )
    
    @staticmethod
    def add_paid_boost(user_id: int, duration_days: int) -> Boost:
        """
        Добавляет платный буст пользователю.
        
        Args:
            user_id: ID пользователя
            duration_days: Длительность буста в днях
            
        Returns:
            Созданный объект Boost
        """
        expires_at = datetime.now() + timedelta(days=duration_days)
        
        return BoostService.add_boost(
            user_id=user_id,
            boost_value=BoostType.PAID,
            expires_at=expires_at
        )
    
    @staticmethod
    def get_active_boosts(user_id: int) -> list[Boost]:
        """
        Получает список активных бустов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список активных бустов
        """
        return BoostRepository.get_active_boosts(user_id)
    
    @staticmethod
    def has_active_boost(user_id: int) -> bool:
        """
        Проверяет, есть ли у пользователя активные бусты.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если есть активные бусты, False в противном случае
        """
        active_boosts = BoostRepository.get_active_boosts(user_id)
        return len(active_boosts) > 0
