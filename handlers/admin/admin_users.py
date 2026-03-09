"""
Обработчики управления администраторами.
Добавление, удаление, изменение ролей администраторов.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from filters.is_admin import IsAdmin
from database.repositories.user_repo import UserRepository
from database.models.settings import AdminUser
from keyboards.inline.admin_keyboard import (
    get_admin_users_keyboard,
    get_admin_role_keyboard,
    get_confirm_keyboard,
    get_admin_main_keyboard
)
from core.constants import AdminRole

logger = logging.getLogger(__name__)

# Создание роутера для управления администраторами
router = Router()

# Инициализация репозиториев
user_repo = UserRepository()


class AddAdminState(StatesGroup):
    """Состояния FSM для добавления администратора."""
    waiting_for_telegram_id = State()
    waiting_for_role = State()


@router.message(Command("list_admins"), IsAdmin(role=AdminRole.OWNER))
async def cmd_list_admins(message: Message):
    """
    Обработчик команды /list_admins.
    Показывает список всех администраторов.
    Доступ: только owner.
    """
    try:
        admins = AdminUser.select().order_by(AdminUser.role.desc(), AdminUser.created_at)
        
        if not admins:
            await message.answer("❌ Администраторы не найдены")
            return
        
        admin_list = "👑 Список администраторов\n\n"
        
        role_emojis = {
            AdminRole.OWNER: "👑",
            AdminRole.ADMIN: "🛡️",
            AdminRole.MODERATOR: "🔨",
            AdminRole.SUPPORT: "💬"
        }
        
        for admin in admins:
            user = admin.user
            emoji = role_emojis.get(admin.role, "👤")
            username = f"@{user.username}" if user.username else f"ID{user.telegram_id}"
            admin_list += (
                f"{emoji} {admin.role.upper()}: {username}\n"
                f"   Telegram ID: {user.telegram_id}\n"
                f"   Назначен: {admin.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
        
        await message.answer(admin_list)
        logger.info(f"Owner {message.from_user.id} просмотрел список администраторов")
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка администраторов: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при получении списка администраторов")


@router.callback_query(F.data == "admin:admins", IsAdmin(role=AdminRole.OWNER))
async def admin_admins_menu(callback: CallbackQuery):
    """
    Обработчик раздела "Администраторы".
    Показывает меню управления администраторами.
    Доступ: только owner.
    """
    admins_text = (
        "👑 Управление администраторами\n\n"
        "Доступно только для owner.\n\n"
        "Команды:\n"
        "/add_admin <telegram_id> <role> - добавить администратора\n"
        "/remove_admin <telegram_id> - удалить администратора\n"
        "/list_admins - показать список администраторов\n\n"
        "Роли: owner, admin, moderator, support"
    )
    
    await callback.message.edit_text(
        admins_text,
        reply_markup=get_admin_users_keyboard()
    )
    await callback.answer()


@router.message(Command("add_admin"), IsAdmin(role=AdminRole.OWNER))
async def cmd_add_admin(message: Message, command):
    """
    Обработчик команды /add_admin <telegram_id> <role>.
    Добавляет нового администратора.
    Доступ: только owner.
    """
    try:
        if not command.args:
            await message.answer(
                "❌ Укажите Telegram ID и роль: /add_admin <telegram_id> <role>\n\n"
                "Роли: owner, admin, moderator, support"
            )
            return
        
        args = command.args.strip().split()
        if len(args) < 2:
            await message.answer(
                "❌ Укажите Telegram ID и роль: /add_admin <telegram_id> <role>\n\n"
                "Роли: owner, admin, moderator, support"
            )
            return
        
        telegram_id = int(args[0])
        role = args[1].lower()
        
        # Проверка роли
        valid_roles = [AdminRole.OWNER, AdminRole.ADMIN, AdminRole.MODERATOR, AdminRole.SUPPORT]
        if role not in valid_roles:
            await message.answer(
                f"❌ Неверная роль. Доступные роли: {', '.join(valid_roles)}"
            )
            return
        
        # Получаем или создаем пользователя
        user = user_repo.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(
                f"❌ Пользователь с Telegram ID {telegram_id} не найден. "
                "Пользователь должен сначала зарегистрироваться в боте."
            )
            return
        
        # Проверяем, не является ли пользователь уже администратором
        try:
            existing_admin = AdminUser.get(AdminUser.user_id == user.id)
            await message.answer(
                f"❌ Пользователь уже является администратором с ролью {existing_admin.role}"
            )
            return
        except AdminUser.DoesNotExist:
            pass
        
        # Создаем администратора
        admin_user = AdminUser.create(
            user=user,
            role=role
        )
        
        # Обновляем роль пользователя в таблице User
        user.role = role
        user.save()
        
        role_emojis = {
            AdminRole.OWNER: "👑",
            AdminRole.ADMIN: "🛡️",
            AdminRole.MODERATOR: "🔨",
            AdminRole.SUPPORT: "💬"
        }
        emoji = role_emojis.get(role, "👤")
        
        await message.answer(
            f"✅ Администратор добавлен\n\n"
            f"{emoji} Роль: {role.upper()}\n"
            f"👤 Пользователь: @{user.username if user.username else f'ID{user.telegram_id}'}\n"
            f"🆔 Telegram ID: {user.telegram_id}"
        )
        
        # Отправляем уведомление пользователю
        try:
            notification_text = (
                f"🎉 Поздравляем!\n\n"
                f"Вам назначена роль администратора: {emoji} {role.upper()}\n\n"
                f"Теперь у вас есть доступ к административной панели бота.\n\n"
                f"Используйте команду /admin или /start для открытия админ-панели."
            )
            await message.bot.send_message(
                chat_id=telegram_id,
                text=notification_text
            )
            logger.info(f"Уведомление отправлено пользователю {telegram_id} о назначении роли {role}")
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление пользователю {telegram_id}: {e}")
        
        logger.info(
            f"Owner {message.from_user.id} добавил администратора {user.id} с ролью {role}"
        )
        
    except ValueError:
        await message.answer("❌ Неверный формат Telegram ID. Используйте число.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при добавлении администратора")


@router.message(Command("remove_admin"), IsAdmin(role=AdminRole.OWNER))
async def cmd_remove_admin(message: Message, command):
    """
    Обработчик команды /remove_admin <telegram_id>.
    Удаляет администратора.
    Доступ: только owner.
    """
    try:
        if not command.args:
            await message.answer("❌ Укажите Telegram ID: /remove_admin <telegram_id>")
            return
        
        telegram_id = int(command.args.strip())
        
        # Получаем пользователя
        user = user_repo.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
            return
        
        # Проверяем, является ли пользователь администратором
        try:
            admin_user = AdminUser.get(AdminUser.user_id == user.id)
            
            # Не позволяем удалять самого себя
            current_user = user_repo.get_by_telegram_id(message.from_user.id)
            if current_user and current_user.id == user.id:
                await message.answer("❌ Вы не можете удалить самого себя")
                return
            
            # Не позволяем удалять других owner (только если это не сам owner)
            if admin_user.role == AdminRole.OWNER:
                await message.answer("❌ Нельзя удалить другого owner")
                return
            
            role = admin_user.role
            admin_user.delete_instance()
            
            # Обновляем роль пользователя обратно на "user"
            user.role = "user"
            user.save()
            
            await message.answer(
                f"✅ Администратор удален\n\n"
                f"👤 Пользователь: @{user.username if user.username else f'ID{user.telegram_id}'}\n"
                f"🆔 Telegram ID: {user.telegram_id}\n"
                f"🗑️ Удалена роль: {role.upper()}"
            )
            
            # Отправляем уведомление пользователю
            try:
                notification_text = (
                    f"ℹ️ Ваша роль администратора была удалена\n\n"
                    f"Роль {role.upper()} больше не активна.\n"
                    f"Вы вернулись к обычному статусу пользователя."
                )
                await message.bot.send_message(
                    chat_id=telegram_id,
                    text=notification_text
                )
                logger.info(f"Уведомление отправлено пользователю {telegram_id} об удалении роли {role}")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {telegram_id}: {e}")
            
            logger.info(
                f"Owner {message.from_user.id} удалил администратора {user.id} с ролью {role}"
            )
            
        except AdminUser.DoesNotExist:
            await message.answer(f"❌ Пользователь не является администратором")
        
    except ValueError:
        await message.answer("❌ Неверный формат Telegram ID. Используйте число.")
    except Exception as e:
        logger.error(f"Ошибка при удалении администратора: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при удалении администратора")


@router.message(Command("change_admin_role"), IsAdmin(role=AdminRole.OWNER))
async def cmd_change_admin_role(message: Message, command):
    """
    Обработчик команды /change_admin_role <telegram_id> <role>.
    Изменяет роль администратора.
    Доступ: только owner.
    """
    try:
        if not command.args:
            await message.answer(
                "❌ Укажите Telegram ID и роль: /change_admin_role <telegram_id> <role>\n\n"
                "Роли: owner, admin, moderator, support"
            )
            return
        
        args = command.args.strip().split()
        if len(args) < 2:
            await message.answer(
                "❌ Укажите Telegram ID и роль: /change_admin_role <telegram_id> <role>\n\n"
                "Роли: owner, admin, moderator, support"
            )
            return
        
        telegram_id = int(args[0])
        new_role = args[1].lower()
        
        # Проверка роли
        valid_roles = [AdminRole.OWNER, AdminRole.ADMIN, AdminRole.MODERATOR, AdminRole.SUPPORT]
        if new_role not in valid_roles:
            await message.answer(
                f"❌ Неверная роль. Доступные роли: {', '.join(valid_roles)}"
            )
            return
        
        # Получаем пользователя
        user = user_repo.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
            return
        
        # Проверяем, является ли пользователь администратором
        try:
            admin_user = AdminUser.get(AdminUser.user_id == user.id)
            old_role = admin_user.role
            
            # Не позволяем изменять роль самого себя на не-owner
            current_user = user_repo.get_by_telegram_id(message.from_user.id)
            if current_user and current_user.id == user.id and new_role != AdminRole.OWNER:
                await message.answer("❌ Вы не можете изменить свою роль на не-owner")
                return
            
            admin_user.role = new_role
            admin_user.save()
            
            # Обновляем роль пользователя в таблице User
            user.role = new_role
            user.save()
            
            role_emojis = {
                AdminRole.OWNER: "👑",
                AdminRole.ADMIN: "🛡️",
                AdminRole.MODERATOR: "🔨",
                AdminRole.SUPPORT: "💬"
            }
            emoji = role_emojis.get(new_role, "👤")
            
            await message.answer(
                f"✅ Роль изменена\n\n"
                f"👤 Пользователь: @{user.username if user.username else f'ID{user.telegram_id}'}\n"
                f"🔄 Старая роль: {old_role.upper()}\n"
                f"{emoji} Новая роль: {new_role.upper()}"
            )
            
            # Отправляем уведомление пользователю
            try:
                notification_text = (
                    f"🔄 Ваша роль администратора изменена\n\n"
                    f"Старая роль: {old_role.upper()}\n"
                    f"Новая роль: {emoji} {new_role.upper()}"
                )
                await message.bot.send_message(
                    chat_id=telegram_id,
                    text=notification_text
                )
                logger.info(f"Уведомление отправлено пользователю {telegram_id} об изменении роли с {old_role} на {new_role}")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {telegram_id}: {e}")
            
            logger.info(
                f"Owner {message.from_user.id} изменил роль администратора {user.id} "
                f"с {old_role} на {new_role}"
            )
            
        except AdminUser.DoesNotExist:
            await message.answer(f"❌ Пользователь не является администратором")
        
    except ValueError:
        await message.answer("❌ Неверный формат Telegram ID. Используйте число.")
    except Exception as e:
        logger.error(f"Ошибка при изменении роли администратора: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при изменении роли")


@router.callback_query(F.data == "admin:add_admin", IsAdmin(role=AdminRole.OWNER))
async def admin_add_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки добавления администратора через callback."""
    await callback.message.answer(
        "Введите Telegram ID пользователя для добавления в администраторы:\n\n"
        "Используйте команду: /add_admin <telegram_id> <role>\n"
        "Роли: owner, admin, moderator, support"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:set_role:"), IsAdmin(role=AdminRole.OWNER))
async def admin_set_role_callback(callback: CallbackQuery):
    """Обработчик изменения роли администратора через callback."""
    try:
        # Формат: admin:set_role:<user_id>:<role>
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        user_id = int(parts[2])
        new_role = parts[3]
        
        # Проверка роли
        valid_roles = [AdminRole.OWNER, AdminRole.ADMIN, AdminRole.MODERATOR, AdminRole.SUPPORT]
        if new_role not in valid_roles:
            await callback.answer("❌ Неверная роль", show_alert=True)
            return
        
        # Получаем пользователя
        user = user_repo.get_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Проверяем, является ли пользователь администратором
        try:
            admin_user = AdminUser.get(AdminUser.user_id == user.id)
            old_role = admin_user.role
            
            # Не позволяем изменять роль самого себя на не-owner
            current_user = user_repo.get_by_telegram_id(callback.from_user.id)
            if current_user and current_user.id == user.id and new_role != AdminRole.OWNER:
                await callback.answer("❌ Вы не можете изменить свою роль на не-owner", show_alert=True)
                return
            
            admin_user.role = new_role
            admin_user.save()
            
            # Обновляем роль пользователя в таблице User
            user.role = new_role
            user.save()
            
            role_emojis = {
                AdminRole.OWNER: "👑",
                AdminRole.ADMIN: "🛡️",
                AdminRole.MODERATOR: "🔨",
                AdminRole.SUPPORT: "💬"
            }
            emoji = role_emojis.get(new_role, "👤")
            
            await callback.answer(f"✅ Роль изменена на {new_role.upper()}")
            await callback.message.edit_reply_markup(
                reply_markup=get_admin_role_keyboard(user_id)
            )
            
            # Отправляем уведомление пользователю
            try:
                notification_text = (
                    f"🔄 Ваша роль администратора изменена\n\n"
                    f"Старая роль: {old_role.upper()}\n"
                    f"Новая роль: {emoji} {new_role.upper()}"
                )
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_text
                )
                logger.info(f"Уведомление отправлено пользователю {user.telegram_id} об изменении роли с {old_role} на {new_role}")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")
            
            logger.info(
                f"Owner {callback.from_user.id} изменил роль администратора {user.id} "
                f"с {old_role} на {new_role}"
            )
            
        except AdminUser.DoesNotExist:
            await callback.answer("❌ Пользователь не является администратором", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при изменении роли через callback: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:remove_admin:"), IsAdmin(role=AdminRole.OWNER))
async def admin_remove_admin_callback(callback: CallbackQuery):
    """Обработчик удаления администратора через callback."""
    try:
        user_id = int(callback.data.split(":")[-1])
        
        # Получаем пользователя
        user = user_repo.get_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Проверяем, является ли пользователь администратором
        try:
            admin_user = AdminUser.get(AdminUser.user_id == user.id)
            
            # Не позволяем удалять самого себя
            current_user = user_repo.get_by_telegram_id(callback.from_user.id)
            if current_user and current_user.id == user.id:
                await callback.answer("❌ Вы не можете удалить самого себя", show_alert=True)
                return
            
            # Не позволяем удалять других owner
            if admin_user.role == AdminRole.OWNER:
                await callback.answer("❌ Нельзя удалить другого owner", show_alert=True)
                return
            
            role = admin_user.role
            admin_user.delete_instance()
            
            # Обновляем роль пользователя обратно на "user"
            user.role = "user"
            user.save()
            
            await callback.answer("✅ Администратор удален")
            await callback.message.edit_text(
                f"✅ Администратор удален\n\n"
                f"👤 Пользователь: @{user.username if user.username else f'ID{user.telegram_id}'}\n"
                f"🆔 Telegram ID: {user.telegram_id}\n"
                f"🗑️ Удалена роль: {role.upper()}",
                reply_markup=get_admin_users_keyboard()
            )
            
            # Отправляем уведомление пользователю
            try:
                notification_text = (
                    f"ℹ️ Ваша роль администратора была удалена\n\n"
                    f"Роль {role.upper()} больше не активна.\n"
                    f"Вы вернулись к обычному статусу пользователя."
                )
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_text
                )
                logger.info(f"Уведомление отправлено пользователю {user.telegram_id} об удалении роли {role}")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")
            
            logger.info(
                f"Owner {callback.from_user.id} удалил администратора {user.id} с ролью {role}"
            )
            
        except AdminUser.DoesNotExist:
            await callback.answer("❌ Пользователь не является администратором", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении администратора через callback: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
