"""
Обработчики очереди модерации.
Обработка действий модераторов через кнопки: подтверждение, отклонение, бан.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from services.moderation_service import ModerationService
from loader import get_bot
from database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

# Создание роутера для модерации
router = Router()

# Инициализация сервисов
user_repo = UserRepository()


async def edit_moderation_message(callback: CallbackQuery, status_text: str):
    """
    Редактирует сообщение модерации, добавляя статус проверки.
    Работает как с фото (caption), так и с текстовыми сообщениями.
    
    Args:
        callback: CallbackQuery объект
        status_text: Текст статуса для добавления
    """
    try:
        message = callback.message
        moderator_name = callback.from_user.username or f"ID{callback.from_user.id}"
        full_status = f"\n\n{status_text} модератором @{moderator_name}"
        
        # Если это фото с caption
        if message.photo and message.caption:
            await message.edit_caption(
                caption=message.caption + full_status,
                reply_markup=None
            )
        # Если это текстовое сообщение
        elif message.text:
            await message.edit_text(
                text=message.text + full_status,
                reply_markup=None
            )
        # Если это фото без caption (маловероятно, но на всякий случай)
        elif message.photo:
            await message.edit_caption(
                caption=full_status.strip(),
                reply_markup=None
            )
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение модерации: {e}")


@router.callback_query(
    F.data.startswith("moderation_approve:")
)
async def handle_approve(callback: CallbackQuery):
    """
    Обработчик кнопки "✅ Подтвердить".
    Одобряет профиль после модерации.
    """
    logger.info(f"Получен callback_query для одобрения: {callback.data} от пользователя {callback.from_user.id}")
    
    # Проверка прав администратора внутри обработчика
    user = callback.from_user
    moderator = user_repo.get_by_telegram_id(user.id)
    
    if not moderator:
        await callback.answer("❌ Ошибка: модератор не найден в базе данных", show_alert=True)
        logger.error(f"Модератор {user.id} не найден в БД")
        return
    
    # Проверка, является ли пользователь администратором
    try:
        from database.models.settings import AdminUser
        admin_user = AdminUser.select().where(AdminUser.user_id == moderator.id).first()
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            logger.warning(f"Пользователь {user.id} (ID в БД: {moderator.id}) не является администратором")
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсинг moderation_id из callback_data
        # Формат: "moderation_approve:123"
        callback_data = callback.data
        moderation_id_str = callback_data.split(":")[-1]
        moderation_id = int(moderation_id_str)
        
        # Инициализация сервиса модерации
        bot = get_bot()
        moderation_service = ModerationService(bot)
        
        # Одобрение профиля
        success = await moderation_service.approve_profile(
            moderation_id=moderation_id,
            moderator_id=moderator.id
        )
        
        if success:
            # Редактирование сообщения с отметкой о проверке
            await edit_moderation_message(callback, "✅ ПРОВЕРЕНО")
            
            await callback.answer("✅ Профиль одобрен", show_alert=False)
            logger.info(f"Профиль одобрен модератором {moderator.id} для задачи {moderation_id}")
        else:
            await callback.answer("❌ Ошибка при одобрении профиля", show_alert=True)
            logger.error(f"Ошибка при одобрении профиля {moderation_id} модератором {moderator.id}")
            
    except ValueError as e:
        await callback.answer("❌ Неверный ID модерации", show_alert=True)
        logger.error(f"Ошибка парсинга moderation_id из callback_data '{callback.data}': {e}")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        logger.error(f"Ошибка при обработке одобрения: {e}", exc_info=True)


@router.callback_query(
    F.data.startswith("moderation_reject:")
)
async def handle_reject(callback: CallbackQuery):
    """
    Обработчик кнопки "❌ Отклонить".
    Отклоняет профиль и запрашивает повторную запись кружка.
    """
    logger.info(f"Получен callback_query для отклонения: {callback.data} от пользователя {callback.from_user.id}")
    
    # Проверка прав администратора внутри обработчика
    user = callback.from_user
    moderator = user_repo.get_by_telegram_id(user.id)
    
    if not moderator:
        await callback.answer("❌ Ошибка: модератор не найден в базе данных", show_alert=True)
        logger.error(f"Модератор {user.id} не найден в БД")
        return
    
    # Проверка, является ли пользователь администратором
    try:
        from database.models.settings import AdminUser
        admin_user = AdminUser.select().where(AdminUser.user_id == moderator.id).first()
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            logger.warning(f"Пользователь {user.id} (ID в БД: {moderator.id}) не является администратором")
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсинг moderation_id из callback_data
        # Формат: "moderation_reject:123"
        callback_data = callback.data
        moderation_id_str = callback_data.split(":")[-1]
        moderation_id = int(moderation_id_str)
        
        # Инициализация сервиса модерации
        bot = get_bot()
        moderation_service = ModerationService(bot)
        
        # Отклонение профиля
        success = await moderation_service.reject_profile(
            moderation_id=moderation_id,
            moderator_id=moderator.id
        )
        
        if success:
            # Редактирование сообщения с отметкой о проверке
            await edit_moderation_message(callback, "❌ ОТКЛОНЕНО")
            
            await callback.answer("❌ Профиль отклонен", show_alert=False)
            logger.info(f"Профиль отклонен модератором {moderator.id} для задачи {moderation_id}")
        else:
            await callback.answer("❌ Ошибка при отклонении профиля", show_alert=True)
            logger.error(f"Ошибка при отклонении профиля {moderation_id} модератором {moderator.id}")
            
    except ValueError as e:
        await callback.answer("❌ Неверный ID модерации", show_alert=True)
        logger.error(f"Ошибка парсинга moderation_id из callback_data '{callback.data}': {e}")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        logger.error(f"Ошибка при обработке отклонения: {e}", exc_info=True)


@router.callback_query(
    F.data.startswith("moderation_ban:")
)
async def handle_ban(callback: CallbackQuery):
    """
    Обработчик кнопки "🚫 Бан".
    Банит пользователя после модерации.
    """
    logger.info(f"Получен callback_query для бана: {callback.data} от пользователя {callback.from_user.id}")
    
    # Проверка прав администратора внутри обработчика
    user = callback.from_user
    moderator = user_repo.get_by_telegram_id(user.id)
    
    if not moderator:
        await callback.answer("❌ Ошибка: модератор не найден в базе данных", show_alert=True)
        logger.error(f"Модератор {user.id} не найден в БД")
        return
    
    # Проверка, является ли пользователь администратором
    try:
        from database.models.settings import AdminUser
        admin_user = AdminUser.select().where(AdminUser.user_id == moderator.id).first()
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            logger.warning(f"Пользователь {user.id} (ID в БД: {moderator.id}) не является администратором")
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсинг moderation_id из callback_data
        # Формат: "moderation_ban:123"
        callback_data = callback.data
        moderation_id_str = callback_data.split(":")[-1]
        moderation_id = int(moderation_id_str)
        
        # Инициализация сервиса модерации
        bot = get_bot()
        moderation_service = ModerationService(bot)
        
        # Бан пользователя
        success = await moderation_service.ban_user(
            moderation_id=moderation_id,
            moderator_id=moderator.id
        )
        
        if success:
            # Редактирование сообщения с отметкой о проверке
            await edit_moderation_message(callback, "🚫 ЗАБАНЕН")
            
            await callback.answer("🚫 Пользователь забанен", show_alert=False)
            logger.info(f"Пользователь забанен модератором {moderator.id} для задачи {moderation_id}")
        else:
            await callback.answer("❌ Ошибка при бане пользователя", show_alert=True)
            logger.error(f"Ошибка при бане пользователя {moderation_id} модератором {moderator.id}")
            
    except ValueError as e:
        await callback.answer("❌ Неверный ID модерации", show_alert=True)
        logger.error(f"Ошибка парсинга moderation_id из callback_data '{callback.data}': {e}")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        logger.error(f"Ошибка при обработке бана: {e}", exc_info=True)
