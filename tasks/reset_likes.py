"""
Фоновая задача для очистки старых данных лайков.
Выполняется ежедневно для поддержания производительности БД.
"""
import logging
from datetime import datetime, timedelta

from database.models.like import Like, ProfileView, ProfileHistory
from core.constants import CLEANUP_PROFILE_HISTORY_DAYS, CLEANUP_PROFILE_VIEWS_DAYS

logger = logging.getLogger(__name__)

# Количество дней для хранения старых записей (по умолчанию 90 дней)
LIKES_CLEANUP_DAYS = 90


async def reset_likes_task():
    """
    Фоновая задача для очистки старых записей лайков, просмотров и истории.
    Выполняется ежедневно.
    
    Удаляет:
    - Старые записи ProfileHistory (старше CLEANUP_PROFILE_HISTORY_DAYS дней)
    - Старые записи ProfileViews (старше CLEANUP_PROFILE_VIEWS_DAYS дней)
    - Опционально: очень старые записи Likes (старше LIKES_CLEANUP_DAYS дней)
    """
    try:
        logger.info("Запуск задачи очистки старых данных лайков...")
        
        now = datetime.now()
        
        # Очистка истории просмотров (ProfileHistory)
        history_cutoff = now - timedelta(days=CLEANUP_PROFILE_HISTORY_DAYS)
        deleted_history = (
            ProfileHistory.delete()
            .where(ProfileHistory.created_at < history_cutoff)
            .execute()
        )
        logger.info(f"Удалено записей истории просмотров: {deleted_history}")
        
        # Очистка просмотров (ProfileViews)
        views_cutoff = now - timedelta(days=CLEANUP_PROFILE_VIEWS_DAYS)
        deleted_views = (
            ProfileView.delete()
            .where(ProfileView.created_at < views_cutoff)
            .execute()
        )
        logger.info(f"Удалено записей просмотров: {deleted_views}")
        
        # Опциональная очистка очень старых лайков (для экономии места)
        # Примечание: по умолчанию лайки не удаляются, так как они используются для статистики
        # Раскомментируйте, если нужно удалять очень старые лайки
        # likes_cutoff = now - timedelta(days=LIKES_CLEANUP_DAYS)
        # deleted_likes = (
        #     Like.delete()
        #     .where(Like.created_at < likes_cutoff)
        #     .execute()
        # )
        # logger.info(f"Удалено старых лайков: {deleted_likes}")
        
        logger.info(
            f"Задача очистки завершена. "
            f"Удалено: история={deleted_history}, просмотры={deleted_views}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи очистки лайков: {e}", exc_info=True)
