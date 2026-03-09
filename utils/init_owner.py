"""
Утилита для инициализации первого owner при запуске бота.
Автоматически создает owner из переменной окружения OWNER_TELEGRAM_ID, если owner еще не существует.
"""
import logging
from typing import Optional

from database.models.settings import AdminUser
from database.repositories.user_repo import UserRepository
from core.constants import AdminRole

logger = logging.getLogger(__name__)


def init_owner_if_needed(owner_telegram_id: Optional[int]) -> bool:
    """
    Инициализирует первого owner, если он еще не существует.
    
    Args:
        owner_telegram_id: Telegram ID для назначения owner. Если None, пропускает инициализацию.
        
    Returns:
        True если owner был создан или уже существует, False если telegram_id не указан
    """
    if owner_telegram_id is None:
        logger.debug("OWNER_TELEGRAM_ID не указан, пропускаем инициализацию owner")
        return False
    
    try:
        # Проверяем, есть ли уже хотя бы один owner
        existing_owner = AdminUser.select().where(
            AdminUser.role == AdminRole.OWNER
        ).first()
        
        if existing_owner:
            logger.info(
                f"Owner уже существует (user_id={existing_owner.user_id}, "
                f"telegram_id={existing_owner.user.telegram_id})"
            )
            return True
        
        # Owner не существует, создаем его
        logger.info(f"Инициализация первого owner для Telegram ID: {owner_telegram_id}")
        
        user_repo = UserRepository()
        
        # Получаем или создаем пользователя
        user = user_repo.get_by_telegram_id(owner_telegram_id)
        if not user:
            # Создаем пользователя, если его еще нет
            user = user_repo.create(
                telegram_id=owner_telegram_id,
                username=None,
                is_active=True,
                is_banned=False,
                is_verified=True
            )
            logger.info(f"Создан новый пользователь для owner: telegram_id={owner_telegram_id}")
        else:
            logger.info(f"Найден существующий пользователь для owner: telegram_id={owner_telegram_id}")
        
        # Проверяем, не является ли пользователь уже администратором с другой ролью
        try:
            existing_admin = AdminUser.get(AdminUser.user_id == user.id)
            # Если уже есть роль, обновляем на owner
            if existing_admin.role != AdminRole.OWNER:
                logger.info(
                    f"Пользователь уже имеет роль {existing_admin.role}, "
                    f"обновляем на {AdminRole.OWNER}"
                )
                existing_admin.role = AdminRole.OWNER
                existing_admin.save()
            else:
                logger.info("Пользователь уже является owner")
            return True
        except AdminUser.DoesNotExist:
            pass
        
        # Создаем owner
        AdminUser.create(
            user=user,
            role=AdminRole.OWNER
        )
        
        logger.info(
            f"✅ Owner успешно инициализирован: "
            f"telegram_id={owner_telegram_id}, user_id={user.id}"
        )
        return True
        
    except Exception as e:
        logger.error(
            f"Ошибка при инициализации owner: {e}",
            exc_info=True
        )
        return False
