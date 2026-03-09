"""
Фоновая задача для очистки старых записей из очереди модерации.
Выполняется ежедневно.
"""
import logging
from datetime import datetime, timedelta

from database.models.moderation import ModerationQueue
from core.constants import CLEANUP_MODERATION_QUEUE_DAYS
from core.constants import ModerationStatus

logger = logging.getLogger(__name__)


async def cleanup_moderation_queue_task():
    """
    Фоновая задача для очистки старых записей из очереди модерации.
    Выполняется ежедневно.
    
    Удаляет записи ModerationQueue, которые:
    - Старше CLEANUP_MODERATION_QUEUE_DAYS дней (по умолчанию 7 дней)
    - Имеют статус APPROVED, REJECTED или BANNED (обработанные)
    - Не удаляет записи со статусом PENDING (ожидающие обработки)
    """
    try:
        logger.info("Запуск задачи очистки очереди модерации...")
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=CLEANUP_MODERATION_QUEUE_DAYS)
        
        # Удаляем только обработанные записи (не PENDING)
        deleted_count = (
            ModerationQueue.delete()
            .where(
                (ModerationQueue.created_at < cutoff_date) &
                (ModerationQueue.status != ModerationStatus.PENDING)
            )
            .execute()
        )
        
        logger.info(f"Удалено записей из очереди модерации: {deleted_count}")
        
        # Дополнительно: проверяем, нет ли очень старых PENDING записей
        # (старше 30 дней) - возможно, они были забыты
        very_old_cutoff = now - timedelta(days=30)
        old_pending = (
            ModerationQueue.select()
            .where(
                (ModerationQueue.status == ModerationStatus.PENDING) &
                (ModerationQueue.created_at < very_old_cutoff)
            )
            .count()
        )
        
        if old_pending > 0:
            logger.warning(
                f"Обнаружено {old_pending} очень старых PENDING записей "
                f"(старше 30 дней). Рекомендуется проверить вручную."
            )
        
        logger.info(f"Задача очистки очереди модерации завершена")
        
    except Exception as e:
        logger.error(
            f"Ошибка при выполнении задачи очистки очереди модерации: {e}",
            exc_info=True
        )
