"""
Обработчики команд администратора.
Команды для управления пользователями, настройками, жалобами.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from filters.is_admin import IsAdmin
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.like_repo import LikeRepository
from database.repositories.complaint_repo import ComplaintRepository
from database.repositories.settings_repo import SettingsRepository
from services.boost_service import BoostService
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
from keyboards.inline.admin_keyboard import (
    get_admin_main_keyboard,
    get_user_actions_keyboard,
    get_settings_keyboard,
    get_confirm_keyboard
)
from loader import get_bot
from core.constants import AdminRole

logger = logging.getLogger(__name__)

# Создание роутера для команд администратора
router = Router()

# Инициализация репозиториев
user_repo = UserRepository()
profile_repo = ProfileRepository()
like_repo = LikeRepository()
complaint_repo = ComplaintRepository()
settings_repo = SettingsRepository()


def format_user_info(target_user, profile=None) -> str:
    """
    Форматирует информацию о пользователе для отображения.
    
    Args:
        target_user: Объект пользователя
        profile: Объект профиля (опционально)
        
    Returns:
        Отформатированная строка с информацией о пользователе
    """
    user_info = (
        f"👤 Пользователь\n\n"
        f"ID: {target_user.id}\n"
        f"Telegram ID: {target_user.telegram_id}\n"
        f"Username: @{target_user.username if target_user.username else 'не указан'}\n"
        f"Забанен: {'✅ Да' if target_user.is_banned else '❌ Нет'}\n"
        f"Верифицирован: {'✅ Да' if target_user.is_verified else '❌ Нет'}\n"
        f"Активен: {'✅ Да' if target_user.is_active else '❌ Нет'}\n"
        f"Создан: {target_user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    
    if profile:
        user_info += f"\n📋 Профиль:\n{format_profile_text(profile)}"
    
    return user_info


async def update_user_info_message(callback: CallbackQuery, target_user, admin_user):
    """
    Обновляет сообщение с информацией о пользователе.
    
    Args:
        callback: CallbackQuery объект
        target_user: Объект пользователя для отображения
        admin_user: Объект администратора для проверки прав
    """
    try:
        profile = profile_repo.get_by_user_id(target_user.id)
        user_info = format_user_info(target_user, profile)
        
        # Если сообщение содержит фото
        if callback.message.photo:
            photo_file_id = get_profile_photo_file_id(profile) if profile else None
            if photo_file_id:
                try:
                    await callback.message.edit_caption(
                        caption=user_info,
                        reply_markup=get_user_actions_keyboard(target_user.id, admin_user)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e).lower():
                        # Если не удалось обновить caption, пробуем обновить только клавиатуру
                        try:
                            await callback.message.edit_reply_markup(
                                reply_markup=get_user_actions_keyboard(target_user.id, admin_user)
                            )
                        except TelegramBadRequest:
                            pass
            else:
                # Если фото нет, обновляем только клавиатуру
                try:
                    await callback.message.edit_reply_markup(
                        reply_markup=get_user_actions_keyboard(target_user.id, admin_user)
                    )
                except TelegramBadRequest:
                    pass
        # Если сообщение содержит текст
        elif callback.message.text:
            try:
                await callback.message.edit_text(
                    text=user_info,
                    reply_markup=get_user_actions_keyboard(target_user.id, admin_user)
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e).lower():
                    # Если не удалось обновить текст, пробуем обновить только клавиатуру
                    try:
                        await callback.message.edit_reply_markup(
                            reply_markup=get_user_actions_keyboard(target_user.id, admin_user)
                        )
                    except TelegramBadRequest:
                        pass
        else:
            # Если нет ни текста, ни фото, обновляем только клавиатуру
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=get_user_actions_keyboard(target_user.id, admin_user)
                )
            except TelegramBadRequest:
                pass
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение с информацией о пользователе: {e}")


class AdminSettingsState(StatesGroup):
    """Состояния FSM для изменения настроек."""
    waiting_for_value = State()


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message):
    """
    Обработчик команды /admin.
    Показывает главное меню админ-панели.
    """
    # Получаем user из контекста или загружаем из БД
    user = user_repo.get_by_telegram_id(message.from_user.id)
    
    admin_text = (
        "👑 Админ-панель\n\n"
        "Выберите раздел для управления:"
    )
    
    await message.answer(
        admin_text,
        reply_markup=get_admin_main_keyboard(user)
    )
    logger.info(f"Администратор {message.from_user.id} открыл админ-панель")


@router.callback_query(F.data == "admin:main", IsAdmin())
async def admin_main_menu(callback: CallbackQuery):
    """Обработчик возврата в главное меню админки."""
    # Получаем user из контекста или загружаем из БД
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    admin_text = (
        "👑 Админ-панель\n\n"
        "Выберите раздел для управления:"
    )
    
    await callback.message.edit_text(
        admin_text,
        reply_markup=get_admin_main_keyboard(user)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users", IsAdmin())
async def admin_users_menu(callback: CallbackQuery):
    """
    Обработчик раздела "Пользователи".
    Показывает меню управления пользователями.
    """
    # Получаем user из контекста или загружаем из БД
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    users_text = (
        "👥 Управление пользователями\n\n"
        "Используйте команды:\n"
        "/find_user <telegram_id> - найти пользователя по Telegram ID\n"
        "/find_user_by_username <username> - найти пользователя по username\n\n"
        "Или выберите действие:"
    )
    
    # Показываем статистику пользователей
    # (можно добавить подсчет через репозиторий)
    
    try:
        # Если сообщение содержит фото, обновляем только клавиатуру
        if callback.message.photo:
            await callback.message.edit_reply_markup(reply_markup=get_admin_main_keyboard(user))
        # Если сообщение содержит текст, обновляем текст и клавиатуру
        elif callback.message.text:
            await callback.message.edit_text(
                users_text,
                reply_markup=get_admin_main_keyboard(user)
            )
        else:
            # Если нет ни текста, ни фото, просто обновляем клавиатуру
            await callback.message.edit_reply_markup(reply_markup=get_admin_main_keyboard(user))
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение в admin_users_menu: {e}")
        # Пытаемся отправить новое сообщение
        try:
            await callback.message.answer(
                users_text,
                reply_markup=get_admin_main_keyboard(user)
            )
        except Exception:
            pass
    
    await callback.answer()


@router.message(Command("find_user"), IsAdmin())
async def cmd_find_user(message: Message, command):
    """
    Обработчик команды /find_user <telegram_id>.
    Находит пользователя по Telegram ID и показывает его данные.
    Доступ: все администраторы.
    """
    try:
        # Получаем user из контекста или загружаем из БД
        user = user_repo.get_by_telegram_id(message.from_user.id)
        
        if not command.args:
            await message.answer("❌ Укажите Telegram ID пользователя: /find_user <telegram_id>")
            return
        
        telegram_id = int(command.args)
        target_user = user_repo.get_by_telegram_id(telegram_id)
        
        if not target_user:
            await message.answer(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
            return
        
        # Получаем профиль пользователя
        profile = profile_repo.get_by_user_id(target_user.id)
        
        user_info = format_user_info(target_user, profile)
        
        # Отправляем фото профиля, если есть
        if profile:
            photo_file_id = get_profile_photo_file_id(profile)
            if photo_file_id:
                await message.answer_photo(
                    photo=photo_file_id,
                    caption=user_info,
                    reply_markup=get_user_actions_keyboard(target_user.id, user)
                )
            else:
                await message.answer(
                    user_info,
                    reply_markup=get_user_actions_keyboard(target_user.id, user)
                )
        else:
            await message.answer(
                user_info,
                reply_markup=get_user_actions_keyboard(target_user.id, user)
            )
        
        logger.info(f"Администратор {message.from_user.id} нашел пользователя {target_user.id}")
        
    except ValueError:
        await message.answer("❌ Неверный формат Telegram ID. Используйте число.")
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при поиске пользователя")


@router.message(Command("find_user_by_username"), IsAdmin())
async def cmd_find_user_by_username(message: Message, command):
    """
    Обработчик команды /find_user_by_username <username>.
    Находит пользователя по username.
    Доступ: все администраторы.
    """
    try:
        # Получаем user из контекста или загружаем из БД
        user = user_repo.get_by_telegram_id(message.from_user.id)
        
        if not command.args:
            await message.answer("❌ Укажите username: /find_user_by_username <username>")
            return
        
        username = command.args.strip().lstrip('@')
        
        # Поиск пользователя по username
        from database.models.user import User
        try:
            target_user = User.get(User.username == username)
        except User.DoesNotExist:
            await message.answer(f"❌ Пользователь с username @{username} не найден")
            return
        
        # Получаем профиль пользователя
        profile = profile_repo.get_by_user_id(target_user.id)
        
        user_info = format_user_info(target_user, profile)
        
        # Отправляем фото профиля, если есть
        if profile:
            photo_file_id = get_profile_photo_file_id(profile)
            if photo_file_id:
                await message.answer_photo(
                    photo=photo_file_id,
                    caption=user_info,
                    reply_markup=get_user_actions_keyboard(target_user.id, user)
                )
            else:
                await message.answer(
                    user_info,
                    reply_markup=get_user_actions_keyboard(target_user.id, user)
                )
        else:
            await message.answer(
                user_info,
                reply_markup=get_user_actions_keyboard(target_user.id, user)
            )
        
        logger.info(f"Администратор {message.from_user.id} нашел пользователя {target_user.id} по username {username}")
        
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя по username: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при поиске пользователя")


@router.callback_query(F.data.startswith("admin:ban:"))
async def admin_ban_user(callback: CallbackQuery):
    """Обработчик бана пользователя. Доступ: moderator и выше."""
    # Получаем пользователя из контекста через репозиторий
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка прав администратора
    try:
        from database.models.settings import AdminUser
        admin_user = AdminUser.select().where(AdminUser.user_id == user.id).first()
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        
        # Проверка роли (moderator и выше)
        if admin_user.role not in [AdminRole.MODERATOR, AdminRole.ADMIN, AdminRole.OWNER]:
            await callback.answer("❌ У вас нет прав для этой операции", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if target_user.is_banned:
            await callback.answer("⚠️ Пользователь уже забанен", show_alert=True)
            return
        
        success = user_repo.ban_user(user_id)
        if success:
            # Обновляем данные пользователя из БД
            target_user = user_repo.get_by_id(user_id)
            
            # Отправляем уведомление пользователю
            bot = get_bot()
            try:
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text="🚫 Вы были забанены администратором. Если вы считаете, что это ошибка, свяжитесь с поддержкой."
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {target_user.telegram_id}: {e}")
            
            # Обновляем сообщение с информацией о пользователе
            await update_user_info_message(callback, target_user, user)
            
            await callback.answer("✅ Пользователь забанен")
            logger.info(f"Администратор {callback.from_user.id} забанил пользователя {user_id}")
        else:
            await callback.answer("❌ Ошибка при бане пользователя", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при бане пользователя: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:unban:"), IsAdmin(role=AdminRole.MODERATOR))
async def admin_unban_user(callback: CallbackQuery, user=None):
    """Обработчик разбана пользователя. Доступ: moderator и выше."""
    try:
        if not user:
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if not target_user.is_banned:
            await callback.answer("⚠️ Пользователь не забанен", show_alert=True)
            return
        
        success = user_repo.unban_user(user_id)
        if success:
            # Обновляем данные пользователя из БД
            target_user = user_repo.get_by_id(user_id)
            
            # Отправляем уведомление пользователю
            bot = get_bot()
            try:
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text="✅ Вы были разбанены администратором. Добро пожаловать обратно!"
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {target_user.telegram_id}: {e}")
            
            # Обновляем сообщение с информацией о пользователе
            await update_user_info_message(callback, target_user, user)
            
            await callback.answer("✅ Пользователь разбанен")
            logger.info(f"Администратор {callback.from_user.id} разбанил пользователя {user_id}")
        else:
            await callback.answer("❌ Ошибка при разбане пользователя", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при разбане пользователя: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:verify:"), IsAdmin(role=AdminRole.ADMIN))
async def admin_verify_user(callback: CallbackQuery, user=None):
    """Обработчик верификации пользователя. Доступ: admin и выше."""
    try:
        if not user:
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if target_user.is_verified:
            await callback.answer("⚠️ Пользователь уже верифицирован", show_alert=True)
            return
        
        success = user_repo.verify_user(user_id)
        if success:
            # Обновляем данные пользователя из БД
            target_user = user_repo.get_by_id(user_id)
            
            # Отправляем уведомление пользователю
            bot = get_bot()
            try:
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text="✅ Ваш аккаунт был верифицирован администратором. Спасибо за использование нашего сервиса!"
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {target_user.telegram_id}: {e}")
            
            # Обновляем сообщение с информацией о пользователе
            await update_user_info_message(callback, target_user, user)
            
            await callback.answer("✅ Пользователь верифицирован")
            logger.info(f"Администратор {callback.from_user.id} верифицировал пользователя {user_id}")
        else:
            await callback.answer("❌ Ошибка при верификации", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при верификации пользователя: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:unverify:"), IsAdmin(role=AdminRole.ADMIN))
async def admin_unverify_user(callback: CallbackQuery, user=None):
    """Обработчик снятия верификации с пользователя. Доступ: admin и выше."""
    try:
        if not user:
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if not target_user.is_verified:
            await callback.answer("⚠️ Пользователь не верифицирован", show_alert=True)
            return
        
        success = user_repo.unverify_user(user_id)
        if success:
            # Обновляем данные пользователя из БД
            target_user = user_repo.get_by_id(user_id)
            
            # Отправляем уведомление пользователю
            bot = get_bot()
            try:
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text="⚠️ Верификация вашего аккаунта была снята администратором. Если у вас есть вопросы, свяжитесь с поддержкой."
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {target_user.telegram_id}: {e}")
            
            # Обновляем сообщение с информацией о пользователе
            await update_user_info_message(callback, target_user, user)
            
            await callback.answer("✅ Верификация снята")
            logger.info(f"Администратор {callback.from_user.id} снял верификацию с пользователя {user_id}")
        else:
            await callback.answer("❌ Ошибка при снятии верификации", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при снятии верификации: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:reset_likes:"), IsAdmin(role=AdminRole.ADMIN))
async def admin_reset_likes(callback: CallbackQuery, user=None):
    """Обработчик сброса лайков пользователя. Доступ: admin и выше."""
    try:
        if not user:
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Удаляем все лайки пользователя
        from database.models.like import Like
        deleted_count = Like.delete().where(
            (Like.from_user_id == user_id) | (Like.to_user_id == user_id)
        ).execute()
        
        await callback.answer(f"✅ Удалено {deleted_count} лайков")
        if callback.message.reply_markup:
            try:
                await callback.message.edit_reply_markup(reply_markup=get_user_actions_keyboard(user_id, user))
            except TelegramBadRequest as e:
                # Игнорируем ошибку, если клавиатура не изменилась
                if "message is not modified" not in str(e).lower():
                    raise
        logger.info(f"Администратор {callback.from_user.id} сбросил лайки пользователя {user_id} ({deleted_count} записей)")
            
    except Exception as e:
        logger.error(f"Ошибка при сбросе лайков: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:boost:"), IsAdmin(role=AdminRole.ADMIN))
async def admin_add_boost(callback: CallbackQuery, user=None):
    """Обработчик добавления буста пользователю. Доступ: admin и выше."""
    try:
        if not user:
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Добавляем платный буст на 7 дней
        from datetime import datetime, timedelta
        boost = BoostService.add_paid_boost(user_id, duration_days=7)
        
        await callback.answer("✅ Буст добавлен (7 дней)")
        if callback.message.reply_markup:
            try:
                await callback.message.edit_reply_markup(reply_markup=get_user_actions_keyboard(user_id, user))
            except TelegramBadRequest as e:
                # Игнорируем ошибку, если клавиатура не изменилась
                if "message is not modified" not in str(e).lower():
                    raise
        logger.info(f"Администратор {callback.from_user.id} добавил буст пользователю {user_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении буста: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:reduce_boost:"), IsAdmin(role=AdminRole.ADMIN))
async def admin_reduce_boost(callback: CallbackQuery, user=None):
    """Обработчик уменьшения буста пользователю. Доступ: admin и выше."""
    try:
        if not user:
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        user_id = int(callback.data.split(":")[-1])
        target_user = user_repo.get_by_id(user_id)
        
        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Добавляем отрицательный буст на 7 дней (уменьшает приоритет)
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=7)
        boost = BoostService.add_boost(user_id, boost_value=-3, expires_at=expires_at)
        
        await callback.answer("✅ Буст уменьшен (7 дней)")
        if callback.message.reply_markup:
            try:
                await callback.message.edit_reply_markup(reply_markup=get_user_actions_keyboard(user_id, user))
            except TelegramBadRequest as e:
                # Игнорируем ошибку, если клавиатура не изменилась
                if "message is not modified" not in str(e).lower():
                    raise
        logger.info(f"Администратор {callback.from_user.id} уменьшил буст пользователю {user_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при уменьшении буста: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:view_profile:"), IsAdmin())
async def admin_view_profile(callback: CallbackQuery):
    """Обработчик просмотра профиля пользователя. Доступ: все администраторы."""
    try:
        # Получаем user из контекста или загружаем из БД
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        user_id = int(callback.data.split(":")[-1])
        profile = profile_repo.get_by_user_id(user_id)
        
        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return
        
        profile_text = format_profile_text(profile)
        photo_file_id = get_profile_photo_file_id(profile)
        
        if photo_file_id:
            await callback.message.answer_photo(
                photo=photo_file_id,
                caption=profile_text,
                reply_markup=get_user_actions_keyboard(user_id, user)
            )
        else:
            await callback.message.answer(
                profile_text,
                reply_markup=get_user_actions_keyboard(user_id, user)
            )
        
        await callback.answer()
            
    except Exception as e:
        logger.error(f"Ошибка при просмотре профиля: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin:settings", IsAdmin(role=AdminRole.ADMIN))
async def admin_settings_menu(callback: CallbackQuery):
    """Обработчик раздела настроек. Доступ: admin и выше."""
    max_likes = settings_repo.get_int("max_likes_per_day", 50)
    boost_frequency = settings_repo.get_int("boost_frequency", 15)
    
    settings_text = (
        "⚙️ Настройки бота\n\n"
        f"❤️ Лимит лайков в день: {max_likes}\n"
        f"🚀 Частота показа буста: каждые {boost_frequency} анкет\n\n"
        "Выберите настройку для изменения:"
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:setting:"), IsAdmin(role=AdminRole.ADMIN))
async def admin_change_setting(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения настройки."""
    setting_key = callback.data.split(":")[-1]
    
    setting_names = {
        "max_likes_per_day": "лимит лайков в день",
        "boost_frequency": "частоту показа буста"
    }
    
    setting_name = setting_names.get(setting_key, setting_key)
    
    await callback.message.answer(
        f"Введите новое значение для {setting_name} (число):"
    )
    
    await state.set_state(AdminSettingsState.waiting_for_value)
    await state.update_data(setting_key=setting_key)
    
    await callback.answer()


@router.message(AdminSettingsState.waiting_for_value, IsAdmin(role=AdminRole.ADMIN))
async def admin_setting_value(message: Message, state: FSMContext):
    """Обработчик ввода значения настройки."""
    try:
        data = await state.get_data()
        setting_key = data.get("setting_key")
        
        value = int(message.text)
        
        if setting_key == "max_likes_per_day" and (value < 1 or value > 1000):
            await message.answer("❌ Лимит лайков должен быть от 1 до 1000")
            return
        
        if setting_key == "boost_frequency" and (value < 1 or value > 100):
            await message.answer("❌ Частота буста должна быть от 1 до 100")
            return
        
        settings_repo.set_int(setting_key, value)
        
        setting_names = {
            "max_likes_per_day": "Лимит лайков в день",
            "boost_frequency": "Частота показа буста"
        }
        
        await message.answer(
            f"✅ {setting_names.get(setting_key, setting_key)} установлен: {value}"
        )
        
        logger.info(f"Администратор {message.from_user.id} изменил настройку {setting_key} на {value}")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        logger.error(f"Ошибка при изменении настройки: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка")
        await state.clear()


@router.callback_query(F.data == "admin:complaints", IsAdmin())
async def admin_complaints_menu(callback: CallbackQuery):
    """Обработчик раздела жалоб. Доступ: все администраторы (просмотр), moderator и выше (управление)."""
    # Получаем user из контекста или загружаем из БД
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    # Получаем количество необработанных жалоб
    from database.models.complaint import Complaint
    from core.constants import ComplaintStatus
    
    pending_count = Complaint.select().where(
        Complaint.status == ComplaintStatus.PENDING
    ).count()
    
    complaints_text = (
        f"🚨 Управление жалобами\n\n"
        f"Необработанных жалоб: {pending_count}\n\n"
        "Используйте админ-панель (Mini App) для просмотра и обработки жалоб."
    )
    
    await callback.message.edit_text(
        complaints_text,
        reply_markup=get_admin_main_keyboard(user)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_complaint_ban:"))
async def admin_complaint_ban(callback: CallbackQuery):
    """
    Обработчик кнопки "🚫 Бан" для жалобы.
    Банит пользователя, на которого пожаловались.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = user_repo.get_by_telegram_id(callback.from_user.id)
    
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
        
        # Проверка роли (moderator и выше)
        if admin_record.role not in [AdminRole.MODERATOR, AdminRole.ADMIN, AdminRole.OWNER]:
            await callback.answer("❌ У вас нет прав для этой операции", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим complaint_id из callback_data
        # Формат: "admin_complaint_ban:{complaint_id}"
        complaint_id = int(callback.data.split(":")[-1])
        
        # Получаем сервис жалоб
        from services.complaint_service import ComplaintService
        bot = get_bot()
        complaint_service = ComplaintService(bot)
        
        # Баним пользователя по жалобе
        success = await complaint_service.ban_user_from_complaint(
            complaint_id=complaint_id,
            moderator_id=admin_user.id
        )
        
        if success:
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
            logger.info(f"Админ {callback.from_user.id} забанил пользователя по жалобе {complaint_id}")
        else:
            await callback.answer("❌ Ошибка при бане пользователя", show_alert=True)
            logger.error(f"Ошибка при бане пользователя по жалобе {complaint_id}")
        
    except ValueError as e:
        await callback.answer("❌ Неверный ID жалобы", show_alert=True)
        logger.error(f"Ошибка парсинга complaint_id из callback_data '{callback.data}': {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке бана по жалобе: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_complaint_dismiss:"))
async def admin_complaint_dismiss(callback: CallbackQuery):
    """
    Обработчик кнопки "✅ Отклонить" для жалобы.
    Отклоняет жалобу без принятия мер.
    """
    # Получаем пользователя-админа из контекста через репозиторий
    admin_user = user_repo.get_by_telegram_id(callback.from_user.id)
    
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
        
        # Проверка роли (moderator и выше)
        if admin_record.role not in [AdminRole.MODERATOR, AdminRole.ADMIN, AdminRole.OWNER]:
            await callback.answer("❌ У вас нет прав для этой операции", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке прав", show_alert=True)
        return
    
    try:
        # Парсим complaint_id из callback_data
        # Формат: "admin_complaint_dismiss:{complaint_id}"
        complaint_id = int(callback.data.split(":")[-1])
        
        # Получаем сервис жалоб
        from services.complaint_service import ComplaintService
        bot = get_bot()
        complaint_service = ComplaintService(bot)
        
        # Отклоняем жалобу
        success = await complaint_service.dismiss_complaint(
            complaint_id=complaint_id,
            moderator_id=admin_user.id
        )
        
        if success:
            # Обновляем сообщение
            try:
                current_text = callback.message.text or (callback.message.caption or "")
                await callback.message.edit_text(
                    current_text + "\n\n✅ Жалоба отклонена",
                    parse_mode="HTML"
                )
            except Exception:
                # Если не удалось отредактировать (например, сообщение с фото), пробуем редактировать caption
                try:
                    if callback.message.photo:
                        current_caption = callback.message.caption or ""
                        await callback.message.edit_caption(
                            caption=current_caption + "\n\n✅ Жалоба отклонена",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.warning(f"Не удалось обновить сообщение: {e}")
            
            await callback.answer("✅ Жалоба отклонена")
            logger.info(f"Админ {callback.from_user.id} отклонил жалобу {complaint_id}")
        else:
            await callback.answer("❌ Ошибка при отклонении жалобы", show_alert=True)
            logger.error(f"Ошибка при отклонении жалобы {complaint_id}")
        
    except ValueError as e:
        await callback.answer("❌ Неверный ID жалобы", show_alert=True)
        logger.error(f"Ошибка парсинга complaint_id из callback_data '{callback.data}': {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке отклонения жалобы: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin:stats", IsAdmin())
async def admin_stats(callback: CallbackQuery):
    """Обработчик раздела статистики. Доступ: все администраторы."""
    # Получаем user из контекста или загружаем из БД
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    from database.models.user import User
    from database.models.profile import Profile
    from database.models.like import Like
    from database.models.match import Match
    
    total_users = User.select().count()
    total_profiles = Profile.select().count()
    total_likes = Like.select().count()
    total_matches = Match.select().count()
    banned_users = User.select().where(User.is_banned == True).count()
    verified_users = User.select().where(User.is_verified == True).count()
    
    stats_text = (
        "📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📋 Всего профилей: {total_profiles}\n"
        f"❤️ Всего лайков: {total_likes}\n"
        f"💕 Всего мэтчей: {total_matches}\n"
        f"🚫 Забаненных: {banned_users}\n"
        f"✅ Верифицированных: {verified_users}\n"
    )
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_main_keyboard(user)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:backup", IsAdmin(role=AdminRole.ADMIN))
async def admin_backup_database(callback: CallbackQuery):
    """
    Обработчик создания бэкапа базы данных.
    Создает копию БД и отправляет файл администратору.
    Доступ: admin и выше.
    """
    try:
        # Получаем user из контекста или загружаем из БД
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        await callback.answer("⏳ Создание бэкапа...")
        
        import os
        import shutil
        from datetime import datetime
        from config import config
        from loader import get_bot
        
        # Получаем путь к базе данных (используем тот же способ, что и в loader.py)
        db_path = config.DATABASE_PATH
        if not os.path.isabs(db_path):
            # Получаем корень проекта (3 уровня вверх от handlers/admin/admin_commands.py)
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            db_path = os.path.join(project_root, db_path)
        
        # Проверяем существование файла БД
        if not os.path.exists(db_path):
            await callback.message.answer("❌ Файл базы данных не найден")
            return
        
        # Создаем имя файла бэкапа с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"dating_bot_backup_{timestamp}.db"
        backup_path = os.path.join(os.path.dirname(db_path), backup_filename)
        
        # Копируем базу данных
        shutil.copy2(db_path, backup_path)
        
        # Отправляем файл администратору
        from aiogram.types import FSInputFile
        
        bot = get_bot()
        
        # Используем FSInputFile для отправки файла
        document = FSInputFile(backup_path, filename=backup_filename)
        
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=document,
            caption=f"💾 Бэкап базы данных\n\nДата создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nРазмер: {os.path.getsize(backup_path) / 1024 / 1024:.2f} MB"
        )
        
        # Удаляем временный файл
        try:
            os.remove(backup_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл бэкапа {backup_path}: {e}")
        
        await callback.message.answer("✅ Бэкап базы данных успешно создан и отправлен")
        logger.info(f"Администратор {callback.from_user.id} создал бэкап базы данных")
        
    except Exception as e:
        logger.error(f"Ошибка при создании бэкапа базы данных: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла ошибка при создании бэкапа")
