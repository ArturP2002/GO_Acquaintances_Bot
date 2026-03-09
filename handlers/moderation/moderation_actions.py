"""
Обработчики для логирования действий модераторов.
Вспомогательные функции для работы с историей модерации.
"""
import logging
from typing import List, Optional
from datetime import datetime

from database.repositories.moderation_repo import ModerationRepository
from database.models.moderation import ModerationAction

logger = logging.getLogger(__name__)

# Инициализация репозитория
moderation_repo = ModerationRepository()


def log_moderation_action(
    moderation_id: int,
    moderator_id: int,
    action: str,
    comment: Optional[str] = None
) -> Optional[ModerationAction]:
    """
    Логирует действие модератора в таблицу ModerationActions.
    
    Args:
        moderation_id: ID задачи модерации
        moderator_id: ID модератора
        action: Действие (approve, reject, ban, etc.)
        comment: Комментарий модератора (опционально)
        
    Returns:
        Созданный объект ModerationAction или None в случае ошибки
    """
    try:
        action_obj = moderation_repo.add_action(
            moderation_id=moderation_id,
            moderator_id=moderator_id,
            action=action,
            comment=comment
        )
        logger.info(
            f"Действие модератора залогировано: "
            f"moderation_id={moderation_id}, moderator_id={moderator_id}, action={action}"
        )
        return action_obj
    except Exception as e:
        logger.error(
            f"Ошибка при логировании действия модератора: {e}",
            exc_info=True
        )
        return None


def get_moderation_actions(moderation_id: int) -> List[ModerationAction]:
    """
    Получает список всех действий по задаче модерации.
    
    Args:
        moderation_id: ID задачи модерации
        
    Returns:
        Список действий по задаче модерации
    """
    try:
        actions = moderation_repo.get_actions(moderation_id)
        return actions
    except Exception as e:
        logger.error(
            f"Ошибка при получении действий модерации {moderation_id}: {e}",
            exc_info=True
        )
        return []


def get_moderator_actions(moderator_id: int, limit: int = 100) -> List[ModerationAction]:
    """
    Получает список действий конкретного модератора.
    
    Args:
        moderator_id: ID модератора
        limit: Максимальное количество записей (по умолчанию 100)
        
    Returns:
        Список действий модератора
    """
    try:
        from database.models.moderation import ModerationAction
        
        actions = list(
            ModerationAction.select()
            .where(ModerationAction.moderator_id == moderator_id)
            .order_by(ModerationAction.created_at.desc())
            .limit(limit)
        )
        return actions
    except Exception as e:
        logger.error(
            f"Ошибка при получении действий модератора {moderator_id}: {e}",
            exc_info=True
        )
        return []


def get_actions_by_date_range(
    start_date: datetime,
    end_date: datetime,
    action_type: Optional[str] = None
) -> List[ModerationAction]:
    """
    Получает список действий модерации за указанный период.
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
        action_type: Тип действия для фильтрации (опционально)
        
    Returns:
        Список действий за период
    """
    try:
        from database.models.moderation import ModerationAction
        
        query = ModerationAction.select().where(
            (ModerationAction.created_at >= start_date) &
            (ModerationAction.created_at <= end_date)
        )
        
        if action_type:
            query = query.where(ModerationAction.action == action_type)
        
        actions = list(query.order_by(ModerationAction.created_at.desc()))
        return actions
    except Exception as e:
        logger.error(
            f"Ошибка при получении действий за период {start_date} - {end_date}: {e}",
            exc_info=True
        )
        return []


def format_action_history(actions: List[ModerationAction]) -> str:
    """
    Форматирует историю действий для отображения.
    
    Args:
        actions: Список действий модерации
        
    Returns:
        Отформатированная строка с историей действий
    """
    if not actions:
        return "История действий пуста."
    
    lines = ["📋 История действий модерации:\n"]
    
    for action in actions:
        action_emoji = {
            "approve": "✅",
            "reject": "❌",
            "ban": "🚫"
        }.get(action.action, "📝")
        
        moderator_name = f"ID{action.moderator_id}"
        try:
            from database.repositories.user_repo import UserRepository
            user_repo = UserRepository()
            moderator = user_repo.get_by_id(action.moderator_id)
            if moderator:
                moderator_name = moderator.username or f"ID{moderator.id}"
        except Exception:
            pass
        
        date_str = action.created_at.strftime("%Y-%m-%d %H:%M:%S")
        comment_str = f"\n   💬 {action.comment}" if action.comment else ""
        
        lines.append(
            f"{action_emoji} <b>{action.action.upper()}</b>\n"
            f"   👤 Модератор: @{moderator_name}\n"
            f"   📅 Дата: {date_str}{comment_str}\n"
        )
    
    return "\n".join(lines)
