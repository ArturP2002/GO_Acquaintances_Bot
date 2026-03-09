"""
Обработчики для действий админов при обнаружении нарушений ИИ.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для обработчиков AI модерации
router = Router()


@router.callback_query(F.data.startswith("ai_moderation:review:"))
async def handle_ai_review(callback: CallbackQuery):
    """
    Обработчик кнопки "👁 Проверить" для просмотра профиля пользователя.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if not admin_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка прав администратора
    try:
        from database.models.settings import AdminUser
        admin_record = AdminUser.select().where(AdminUser.user_id == admin_user.id).first()
        if not admin_record:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим данные из callback_data: ai_moderation:review:user_id:check_type
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        user_id = int(parts[2])
        check_type = parts[3]
        
        # Получаем пользователя и профиль
        user = UserRepository.get_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        profile = ProfileRepository.get_by_user_id(user.id)
        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return
        
        # Форматируем информацию о профиле
        from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
        
        profile_text = format_profile_text(profile)
        profile_text += f"\n\n🔍 Проверка ИИ: {check_type}"
        
        photo_file_id = get_profile_photo_file_id(profile)
        
        bot = get_bot()
        
        if photo_file_id:
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo_file_id,
                caption=profile_text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text=profile_text,
                parse_mode="HTML"
            )
        
        await callback.answer("✅ Профиль отправлен")
        logger.info(f"Админ {callback.from_user.id} просмотрел профиль пользователя {user_id} после AI проверки")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке просмотра профиля: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("ai_moderation:ban:"))
async def handle_ai_ban(callback: CallbackQuery):
    """
    Обработчик кнопки "🚫 Бан" для бана пользователя после проверки ИИ.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if not admin_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка прав администратора
    try:
        from database.models.settings import AdminUser
        admin_record = AdminUser.select().where(AdminUser.user_id == admin_user.id).first()
        if not admin_record:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим данные из callback_data: ai_moderation:ban:user_id:check_type
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        user_id = int(parts[2])
        check_type = parts[3]
        
        # Получаем пользователя
        user = UserRepository.get_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Баним пользователя
        if not user.is_banned:
            UserRepository.ban_user(user_id)
            
            # Уведомляем пользователя (только если это не тестовый пользователь с отрицательным telegram_id)
            if user.telegram_id > 0:
                bot = get_bot()
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "🚫 Ваш аккаунт был заблокирован администратором "
                            "из-за нарушения правил сообщества.\n\n"
                            f"Тип нарушения: {check_type}\n\n"
                            "Если вы считаете, что это ошибка, свяжитесь с поддержкой."
                        )
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            else:
                logger.info(f"Пропущена отправка уведомления тестовому пользователю {user_id} (telegram_id: {user.telegram_id})")
            
            # Обновляем сообщение
            try:
                current_text = callback.message.text or (callback.message.caption or "")
                await callback.message.edit_text(
                    current_text + "\n\n✅ Пользователь забанен",
                    parse_mode="HTML"
                )
            except Exception:
                # Если не удалось отредактировать (например, сообщение с фото), пробуем редактировать caption
                try:
                    if callback.message.photo:
                        current_caption = callback.message.caption or ""
                        await callback.message.edit_caption(
                            caption=current_caption + "\n\n✅ Пользователь забанен",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.warning(f"Не удалось обновить сообщение: {e}")
            
            await callback.answer("✅ Пользователь забанен")
            logger.info(f"Админ {callback.from_user.id} забанил пользователя {user_id} после AI проверки")
        else:
            await callback.answer("⚠️ Пользователь уже забанен", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при бане пользователя: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("ai_moderation:allow:"))
async def handle_ai_allow(callback: CallbackQuery):
    """
    Обработчик кнопки "✔ Разрешить" для разрешения контента после проверки ИИ.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if not admin_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка прав администратора
    try:
        from database.models.settings import AdminUser
        admin_record = AdminUser.select().where(AdminUser.user_id == admin_user.id).first()
        if not admin_record:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим данные из callback_data: ai_moderation:allow:user_id:check_type
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        user_id = int(parts[2])
        check_type = parts[3]
        
        # Получаем пользователя
        user = UserRepository.get_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Если пользователь был забанен автоматически, разбаниваем
        if user.is_banned:
            UserRepository.unban_user(user_id)
            
            # Уведомляем пользователя (только если это не тестовый пользователь с отрицательным telegram_id)
            if user.telegram_id > 0:
                bot = get_bot()
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "✅ Ваш аккаунт был разблокирован администратором.\n\n"
                            "Извините за неудобства. Вы можете продолжать пользоваться ботом."
                        )
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            else:
                logger.info(f"Пропущена отправка уведомления тестовому пользователю {user_id} (telegram_id: {user.telegram_id})")
        
        # Обновляем сообщение
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ Контент разрешен администратором",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Контент разрешен")
        logger.info(f"Админ {callback.from_user.id} разрешил контент пользователя {user_id} после AI проверки")
        
    except Exception as e:
        logger.error(f"Ошибка при разрешении контента: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("ai_decision:correct:"))
async def handle_ai_decision_correct(callback: CallbackQuery):
    """
    Обработчик кнопки "✅ Верно" - админ подтверждает правильность решения ИИ.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if not admin_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка прав администратора
    try:
        from database.models.settings import AdminUser
        admin_record = AdminUser.select().where(AdminUser.user_id == admin_user.id).first()
        if not admin_record:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим данные из callback_data: ai_decision:correct:user_id:check_type
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        user_id = int(parts[2])
        check_type = parts[3]
        
        # Получаем информацию об админе
        admin_username = callback.from_user.username
        admin_name = callback.from_user.first_name or "Администратор"
        admin_text = f"@{admin_username}" if admin_username else admin_name
        
        # Обновляем сообщение (может быть как с фото, так и без)
        try:
            if callback.message.photo:
                # Сообщение с фото
                current_caption = callback.message.caption or ""
                new_caption = current_caption + f"\n\n✅ <b>Проверено: {admin_text}</b>"
                await callback.message.edit_caption(
                    caption=new_caption,
                    parse_mode="HTML"
                )
            else:
                # Сообщение без фото
                current_text = callback.message.text or ""
                new_text = current_text + f"\n\n✅ <b>Проверено: {admin_text}</b>"
                await callback.message.edit_text(
                    text=new_text,
                    parse_mode="HTML"
                )
        except Exception as edit_error:
            logger.warning(f"Не удалось обновить сообщение: {edit_error}")
            # Пытаемся отправить новое сообщение
            try:
                if callback.message.photo:
                    current_caption = callback.message.caption or ""
                    new_caption = current_caption + f"\n\n✅ <b>Проверено: {admin_text}</b>"
                    await callback.message.answer(
                        text=new_caption,
                        parse_mode="HTML"
                    )
                else:
                    current_text = callback.message.text or ""
                    new_text = current_text + f"\n\n✅ <b>Проверено: {admin_text}</b>"
                    await callback.message.answer(
                        text=new_text,
                        parse_mode="HTML"
                    )
            except Exception:
                pass
        
        await callback.answer("✅ Решение ИИ подтверждено")
        logger.info(f"Админ {callback.from_user.id} ({admin_text}) подтвердил решение ИИ для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении решения ИИ: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("ai_decision:incorrect:"))
async def handle_ai_decision_incorrect(callback: CallbackQuery):
    """
    Обработчик кнопки "❌ Неверно" - админ опровергает решение ИИ.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if not admin_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка прав администратора
    try:
        from database.models.settings import AdminUser
        admin_record = AdminUser.select().where(AdminUser.user_id == admin_user.id).first()
        if not admin_record:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим данные из callback_data: ai_decision:incorrect:user_id:check_type
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        user_id = int(parts[2])
        check_type = parts[3]
        
        # Получаем пользователя
        user = UserRepository.get_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Получаем информацию об админе
        admin_username = callback.from_user.username
        admin_name = callback.from_user.first_name or "Администратор"
        admin_text = f"@{admin_username}" if admin_username else admin_name
        
        # Разблокируем пользователя (если заблокирован)
        was_banned = user.is_banned
        if user.is_banned:
            UserRepository.unban_user(user_id)
            logger.info(f"Пользователь {user_id} разблокирован админом {callback.from_user.id}")
            
            # Уведомляем пользователя (только если это не тестовый пользователь с отрицательным telegram_id)
            if user.telegram_id > 0:
                bot = get_bot()
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "✅ Администратор проверил вашу анкету и снял блокировку.\n\n"
                            "Извините за неудобства. Вы можете продолжать пользоваться ботом."
                        )
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            else:
                logger.info(f"Пропущена отправка уведомления тестовому пользователю {user_id} (telegram_id: {user.telegram_id})")
        
        # Обновляем сообщение (может быть как с фото, так и без)
        try:
            if callback.message.photo:
                # Сообщение с фото
                current_caption = callback.message.caption or ""
                ban_text = " (пользователь разблокирован)" if was_banned else ""
                new_caption = current_caption + f"\n\n❌ <b>Решение ИИ опровергнуто: {admin_text}</b>{ban_text}"
                await callback.message.edit_caption(
                    caption=new_caption,
                    parse_mode="HTML"
                )
            else:
                # Сообщение без фото
                current_text = callback.message.text or ""
                ban_text = " (пользователь разблокирован)" if was_banned else ""
                new_text = current_text + f"\n\n❌ <b>Решение ИИ опровергнуто: {admin_text}</b>{ban_text}"
                await callback.message.edit_text(
                    text=new_text,
                    parse_mode="HTML"
                )
        except Exception as edit_error:
            logger.warning(f"Не удалось обновить сообщение: {edit_error}")
            # Пытаемся отправить новое сообщение
            try:
                if callback.message.photo:
                    current_caption = callback.message.caption or ""
                    ban_text = " (пользователь разблокирован)" if was_banned else ""
                    new_caption = current_caption + f"\n\n❌ <b>Решение ИИ опровергнуто: {admin_text}</b>{ban_text}"
                    await callback.message.answer(
                        text=new_caption,
                        parse_mode="HTML"
                    )
                else:
                    current_text = callback.message.text or ""
                    ban_text = " (пользователь разблокирован)" if was_banned else ""
                    new_text = current_text + f"\n\n❌ <b>Решение ИИ опровергнуто: {admin_text}</b>{ban_text}"
                    await callback.message.answer(
                        text=new_text,
                        parse_mode="HTML"
                    )
            except Exception:
                pass
        
        await callback.answer("❌ Решение ИИ опровергнуто")
        logger.info(f"Админ {callback.from_user.id} ({admin_text}) опроверг решение ИИ для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при опровержении решения ИИ: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
