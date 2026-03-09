"""
Фоновая задача для очистки истекших бустов анкет.
Выполняется ежедневно.
"""
import logging
from datetime import datetime

from database.repositories.boost_repo import BoostRepository

logger = logging.getLogger(__name__)


async def profile_boost_rotation_task():
    """
    Фоновая задача для очистки истекших бустов анкет.
    Выполняется ежедневно.
    
    Удаляет все записи из таблицы Boosts, у которых:
    - expires_at < NOW() (истекшие бусты)
    - expires_at не NULL (бессрочные бусты не удаляются)
    """
    try:
        logger.info("Запуск задачи очистки истекших бустов...")
        
        # Используем метод из репозитория для удаления истекших бустов
        deleted_count = BoostRepository.delete_expired()
        
        logger.info(f"Удалено истекших бустов: {deleted_count}")
        
        if deleted_count > 0:
            logger.info(
                f"Задача очистки истекших бустов завершена. "
                f"Удалено записей: {deleted_count}"
            )
        else:
            logger.debug("Истекших бустов не найдено")
        
    except Exception as e:
        logger.error(
            f"Ошибка при выполнении задачи очистки истекших бустов: {e}",
            exc_info=True
        )
