"""
Фоновая задача для автоматической заморозки анкет неактивных пользователей.
Выполняется ежедневно для заморозки анкет пользователей, которые не были активны более 10 дней.
"""
import logging
from datetime import datetime, timedelta

from database.models.user import User
from database.repositories.profile_repo import ProfileRepository

logger = logging.getLogger(__name__)

# Количество дней неактивности для заморозки анкеты
INACTIVE_DAYS_THRESHOLD = 10


async def freeze_inactive_profiles_task():
    """
    Фоновая задача для автоматической заморозки анкет неактивных пользователей.
    Выполняется ежедневно.
    
    Логика:
    1. Находит всех пользователей с is_active=True, которые не были активны более 10 дней
    2. Устанавливает is_active=False для таких пользователей
    3. Логирует количество замороженных анкет
    
    Примечание: Пользователи не банируются (is_banned остается False),
    просто их анкеты перестают предлагаться другим пользователям.
    """
    try:
        logger.info("Запуск задачи заморозки неактивных анкет...")
        
        # Вычисляем пороговую дату (10 дней назад)
        threshold_date = datetime.now() - timedelta(days=INACTIVE_DAYS_THRESHOLD)
        
        # Находим активных пользователей, которые не были активны более 10 дней
        # Исключаем забаненных пользователей (они уже не показываются)
        inactive_users = list(
            User.select()
            .where(
                (User.is_active == True) &
                (User.is_banned == False) &
                (
                    (User.last_active.is_null()) |  # Если last_active не установлен, считаем неактивным
                    (User.last_active < threshold_date)
                )
            )
        )
        
        frozen_count = 0
        
        for user in inactive_users:
            try:
                # Проверяем, есть ли у пользователя профиль
                profile = ProfileRepository.get_by_user_id(user.id)
                if profile:
                    # Замораживаем анкету (устанавливаем is_active=False)
                    user.is_active = False
                    user.save()
                    frozen_count += 1
                    logger.debug(
                        f"Анкета пользователя {user.telegram_id} заморожена "
                        f"(последняя активность: {user.last_active})"
                    )
            except Exception as e:
                logger.error(
                    f"Ошибка при заморозке анкеты пользователя {user.telegram_id}: {e}",
                    exc_info=True
                )
        
        logger.info(
            f"Задача заморозки неактивных анкет завершена. "
            f"Заморожено анкет: {frozen_count} из {len(inactive_users)} неактивных пользователей"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи заморозки неактивных анкет: {e}", exc_info=True)
