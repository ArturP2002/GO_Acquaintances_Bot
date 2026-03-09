"""
Обработчики лайков.
Обработка лайков, создание мэтчей, автоматический показ следующей анкеты.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from services.like_service import LikeService
from handlers.user.browse_profiles import show_next_profile
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
from keyboards.inline.profile_keyboard import get_profile_keyboard
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для лайков
router = Router()

# Инициализация репозиториев
user_repo = UserRepository()
profile_repo = ProfileRepository()


@router.callback_query(F.data.startswith("like:"))
async def like_profile(callback: CallbackQuery):
    """
    Обработчик кнопки "❤️ Лайк".
    Обрабатывает лайк, проверяет мэтч, автоматически показывает следующую анкету.
    
    Callback data format: "like:{target_user_id}"
    
    Args:
        callback: CallbackQuery объект
    """
    # Получаем пользователя из контекста через репозиторий
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        logger.error(f"Пользователь не найден в контексте для callback {callback.data}")
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await callback.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.", show_alert=True)
        return
    
    try:
        # Парсим target_user_id из callback.data
        # Формат: "like:{target_user_id}"
        callback_data = callback.data
        if not callback_data.startswith("like:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            logger.error(f"Неверный формат callback data: {callback_data}")
            return
        
        try:
            target_user_id = int(callback_data.split(":")[1])
            logger.debug(f"Парсинг callback_data: {callback_data} -> target_user_id={target_user_id}")
        except (ValueError, IndexError) as e:
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            logger.error(f"Не удалось распарсить user_id из callback data: {callback_data}, ошибка: {e}")
            return
        
        logger.info(f"Обработка лайка: пользователь {user.id} (telegram_id={user.telegram_id}) лайкает пользователя {target_user_id}")
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис лайков
        like_service = LikeService(bot)
        
        # Добавляем лайк
        logger.debug(f"Вызов like_service.add_like(from_user_id={user.id}, to_user_id={target_user_id})")
        success, error_message, has_match, is_new_like = like_service.add_like(
            from_user_id=user.id,
            to_user_id=target_user_id
        )
        logger.debug(f"Результат add_like: success={success}, error_message={error_message}, has_match={has_match}, is_new_like={is_new_like}")
        
        if not success:
            # Если ошибка (например, лимит превышен)
            await callback.answer(error_message or "Ошибка при добавлении лайка", show_alert=True)
            logger.warning(f"Не удалось добавить лайк от {user.id} к {target_user_id}: {error_message}")
            return
        
        # Если есть мэтч - создаем его и уведомляем пользователей
        if has_match:
            try:
                await like_service.create_match(user.id, target_user_id)
                logger.info(f"Создан мэтч между пользователями {user.id} и {target_user_id}")
                
                # Показываем уведомление о мэтче
                await callback.answer("🎉 У вас взаимная симпатия!", show_alert=True)
            except Exception as e:
                logger.error(f"Ошибка при создании мэтча между {user.id} и {target_user_id}: {e}", exc_info=True)
                # Продолжаем выполнение даже если не удалось создать мэтч
        else:
            # Просто подтверждаем лайк
            await callback.answer("❤️ Лайк поставлен!")
            
            # Отправляем уведомление пользователю, которому поставили лайк
            # (только если лайк был создан только что и нет мэтча, при мэтче отправляется другое уведомление)
            if is_new_like:
                logger.info(f"Отправка уведомления о лайке от {user.id} к {target_user_id} (is_new_like=True)")
                try:
                    notification_sent = await like_service.notify_about_like(
                        from_user_id=user.id,
                        to_user_id=target_user_id
                    )
                    if notification_sent:
                        logger.info(f"Уведомление о лайке успешно отправлено пользователю {target_user_id}")
                    else:
                        logger.warning(f"Уведомление о лайке не было отправлено пользователю {target_user_id} (вернулось False)")
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке уведомления о лайке от {user.id} к {target_user_id}: {e}",
                        exc_info=True
                    )
                    # Не прерываем выполнение, если уведомление не отправилось
            else:
                logger.debug(f"Уведомление о лайке не отправляется: is_new_like=False (лайк уже существовал или произошла ошибка)")
        
        # Автоматически показываем следующую анкету
        await show_next_profile(callback, user.id)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке лайка для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при обработке лайка", show_alert=True)


async def show_liker_profile(callback: CallbackQuery, liker_user_id: int, viewer_user_id: int):
    """
    Показывает анкету пользователя, который поставил лайк.
    
    Args:
        callback: CallbackQuery объект
        liker_user_id: ID пользователя, который поставил лайк (в БД)
        viewer_user_id: ID пользователя, который просматривает анкету (в БД)
    """
    try:
        # Получаем профиль пользователя, который поставил лайк
        liker_profile = profile_repo.get_by_user_id(liker_user_id)
        if not liker_profile:
            await callback.answer("❌ Анкета не найдена", show_alert=True)
            logger.warning(f"Профиль пользователя {liker_user_id} не найден")
            return
        
        # Проверяем, не забанен ли пользователь
        liker_user = user_repo.get_by_id(liker_user_id)
        if not liker_user or liker_user.is_banned:
            await callback.answer("❌ Этот пользователь больше не доступен", show_alert=True)
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(liker_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(liker_profile)
        
        # Добавляем пометку, что это пользователь, который поставил лайк
        profile_text = f"❤️ <b>Вам поставил лайк:</b>\n\n{profile_text}"
        
        # Создаем клавиатуру с кнопками для взаимодействия
        keyboard = get_profile_keyboard(
            profile_id=liker_profile.id,
            user_id=liker_user_id
        )
        
        # Записываем просмотр в ProfileViews, чтобы эта анкета не показывалась в обычном просмотре
        profile_repo.add_view(viewer_id=viewer_user_id, profile_id=liker_profile.id)
        logger.debug(f"Просмотр анкеты {liker_profile.id} пользователем {viewer_user_id} записан (через уведомление о лайке)")
        
        # Добавляем профиль в историю для кнопки "Назад"
        profile_repo.add_to_history(user_id=viewer_user_id, profile_id=liker_profile.id)
        logger.debug(f"Анкета {liker_profile.id} добавлена в историю для пользователя {viewer_user_id}")
        
        # Отправляем или редактируем сообщение
        if photo_file_id:
            # Если есть фото
            if callback.message.photo:
                # Если сообщение уже содержит фото - редактируем
                try:
                    from aiogram.types import InputMediaPhoto
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=photo_file_id, caption=profile_text),
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception:
                    # Если не удалось отредактировать, отправляем новое
                    await callback.message.answer_photo(
                        photo=photo_file_id,
                        caption=profile_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
            else:
                # Если текущее сообщение текстовое, отправляем новое с фото
                await callback.message.answer_photo(
                    photo=photo_file_id,
                    caption=profile_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            # Если фото нет - отправляем текстовое сообщение
            if callback.message.photo:
                # Если текущее сообщение с фото, отправляем новое текстовое
                await callback.message.answer(
                    text=profile_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            elif callback.message.text:
                # Если текущее сообщение текстовое - редактируем
                await callback.message.edit_text(
                    text=profile_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                # Если неизвестный тип - отправляем новое
                await callback.message.answer(
                    text=profile_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        
        await callback.answer()
        logger.info(f"Показана анкета пользователя {liker_user_id} пользователю {viewer_user_id}")
        
    except Exception as e:
        logger.error(
            f"Ошибка при показе анкеты пользователя {liker_user_id} пользователю {viewer_user_id}: {e}",
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка при загрузке анкеты", show_alert=True)


@router.callback_query(F.data.startswith("view_liker_profile:"))
async def handle_view_liker_profile(callback: CallbackQuery):
    """
    Обработчик кнопки "Просмотреть анкету" в уведомлении о лайке.
    Показывает анкету пользователя, который поставил лайк.
    
    Args:
        callback: CallbackQuery объект
    """
    # Получаем пользователя из контекста
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        logger.error(f"Пользователь не найден в контексте для callback {callback.data}")
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await callback.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.", show_alert=True)
        return
    
    try:
        # Парсим liker_user_id из callback.data
        # Формат: "view_liker_profile:{liker_user_id}"
        callback_data = callback.data
        if not callback_data.startswith("view_liker_profile:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        try:
            liker_user_id = int(callback_data.split(":")[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        # Показываем анкету
        await show_liker_profile(callback, liker_user_id, user.id)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке просмотра анкеты лайкера для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("skip_like_notification:"))
async def handle_skip_like_notification(callback: CallbackQuery):
    """
    Обработчик кнопки "Пропустить" в уведомлении о лайке.
    Удаляет уведомление или показывает подтверждение.
    
    Args:
        callback: CallbackQuery объект
    """
    # Получаем пользователя из контекста
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    try:
        # Парсим liker_user_id из callback.data (для логирования)
        callback_data = callback.data
        liker_user_id = None
        if callback_data.startswith("skip_like_notification:"):
            try:
                liker_user_id = int(callback_data.split(":")[1])
            except (ValueError, IndexError):
                pass
        
        # Удаляем сообщение с уведомлением
        try:
            await callback.message.delete()
            logger.debug(f"Пользователь {user.id} пропустил уведомление о лайке от {liker_user_id}")
        except Exception as e:
            # Если не удалось удалить, просто подтверждаем
            logger.debug(f"Не удалось удалить сообщение с уведомлением о лайке: {e}")
            await callback.answer("Уведомление пропущено")
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке пропуска уведомления о лайке для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
