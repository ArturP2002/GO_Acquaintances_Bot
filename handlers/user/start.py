"""
Обработчик команды /start для пользователей.
Проверяет регистрацию, обрабатывает реферальные ссылки и показывает меню.
Для owner показывает админ-панель.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.settings_repo import SettingsRepository
from core.cache import invalidate_user_cache
from keyboards.reply.main_menu import get_main_menu_keyboard, get_registration_menu_keyboard
from keyboards.inline.admin_keyboard import get_admin_main_keyboard
from handlers.user.referrals import process_referral_link_async
from handlers.user.registration import get_gender_keyboard
from utils.admin_roles import get_user_role
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
from states.profile_edit_state import ProfileEditState
from core.constants import AdminRole, MIN_AGE_DEFAULT
from config import config
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для команд пользователя
router = Router()

# Инициализация репозиториев
user_repo = UserRepository()
profile_repo = ProfileRepository()


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    """
    Обработчик команды /start.
    
    Функционал:
    1. Проверяет, является ли пользователь owner - если да, показывает админ-панель
    2. Проверяет, зарегистрирован ли пользователь (есть ли профиль)
    3. Парсит реферальный код из аргументов команды (если есть)
    4. Показывает главное меню (если зарегистрирован) или предложение регистрации
    5. Сохраняет реферальный код в FSM для использования при регистрации
    """
    telegram_id = message.from_user.id
    username = message.from_user.username
    
    # Получение или создание пользователя
    user = user_repo.get_by_telegram_id(telegram_id)
    if not user:
        # Создаем пользователя, если его еще нет
        user = user_repo.create(
            telegram_id=telegram_id,
            username=username
        )
        logger.info(f"Создан новый пользователь: telegram_id={telegram_id}, username={username}")
    
    # Обновление времени последней активности
    user_repo.update_last_active(user.id)
    
    # Обновление username, если он изменился
    if user.username != username:
        user.username = username
        user.save()
    
    # Проверка, является ли пользователь администратором
    user_role = get_user_role(user)
    is_admin = user_role is not None
    
    if is_admin:
        # Показываем админ-панель для всех администраторов
        role_emojis = {
            AdminRole.OWNER: "👑",
            AdminRole.ADMIN: "🛡️",
            AdminRole.MODERATOR: "🔨",
            AdminRole.SUPPORT: "💬"
        }
        role_names = {
            AdminRole.OWNER: "Панель владельца",
            AdminRole.ADMIN: "Админ-панель",
            AdminRole.MODERATOR: "Панель модератора",
            AdminRole.SUPPORT: "Панель поддержки"
        }
        
        emoji = role_emojis.get(user_role, "👤")
        role_name = role_names.get(user_role, "Админ-панель")
        
        admin_text = (
            f"{emoji} {role_name}\n\n"
            f"Роль: {user_role.upper()}\n\n"
            "Выберите раздел для управления:"
        )
        
        await message.answer(
            admin_text,
            reply_markup=get_admin_main_keyboard(user)
        )
        logger.info(f"Администратор {telegram_id} (роль: {user_role}) открыл панель через /start")
        return
    
    # Проверяем, забанен ли пользователь (только для не-администраторов)
    if not is_admin and user.is_banned:
        await message.answer(
            "🚫 Вы были заблокированы. Обратитесь к администратору."
        )
        logger.info(f"Забаненный пользователь {telegram_id} попытался зайти в бот")
        return
    
    # Обработка реферального кода из аргументов команды
    referral_code = command.args if command and command.args else None
    
    # Обрабатываем реферальную ссылку, если есть
    if referral_code:
        await process_referral_link_async(message, referral_code, state)
    
    profile = profile_repo.get_by_user_id(user.id)
    
    if profile:
        # Проверяем, прошел ли пользователь модерацию
        if user.is_verified:
            # Пользователь зарегистрирован и верифицирован - показываем главное меню
            await message.answer(
                "👋 Добро пожаловать обратно!\n\n"
                "Выберите действие из меню:",
                reply_markup=get_main_menu_keyboard()
            )
            logger.info(f"Пользователь {telegram_id} зашел в бот (зарегистрирован и верифицирован)")
        else:
            # Пользователь зарегистрирован, но не прошел модерацию
            await message.answer(
                "⏳ Ваша анкета находится на модерации.\n\n"
                "Пожалуйста, дождитесь проверки модератором. "
                "Вы получите уведомление, когда ваша анкета будет одобрена."
            )
            logger.info(f"Пользователь {telegram_id} зашел в бот (зарегистрирован, но не верифицирован)")
    else:
        # Пользователь не зарегистрирован - предлагаем регистрацию
        welcome_text = (
            "👋 Привет! Добро пожаловать в бот знакомств!\n\n"
            "Здесь ты сможешь найти интересных людей и завести новые знакомства.\n\n"
            "Для начала работы нужно пройти регистрацию. Следуй инструкциям бота!"
        )
        
        # Если есть реферальный код, добавляем информацию
        if referral_code:
            welcome_text += f"\n\n🎁 Ты перешел по реферальной ссылке! После регистрации пригласивший получит награду."
        
        await message.answer(
            welcome_text,
            reply_markup=get_registration_menu_keyboard()
        )
        logger.info(f"Пользователь {telegram_id} зашел в бот (не зарегистрирован)")


@router.message(F.text == "👤 Мой профиль")
async def show_my_profile(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "👤 Мой профиль".
    Показывает профиль текущего пользователя.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста (добавлен UserContextMiddleware)
    """
    logger.info(f"Обработчик show_my_profile вызван для пользователя {message.from_user.id}")
    
    # Очищаем состояние FSM, если пользователь в процессе регистрации
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        logger.debug(f"Очищено состояние FSM для пользователя {message.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте и БД для показа профиля")
            return
    
    try:
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await message.answer("❌ Ваш профиль не найден. Пожалуйста, завершите регистрацию.")
            return
        
        # Форматируем текст профиля
        profile_text = format_profile_text(profile)
        
        # Добавляем информацию о настройках поиска
        profile_text += (
            f"\n\n🔍 Настройки поиска:\n"
            f"Возраст: {profile.min_age_preference}-{profile.max_age_preference} лет"
        )
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(profile)
        
        # Создаем клавиатуру для редактирования профиля
        edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать анкету",
                    callback_data="edit_profile"
                )
            ]
        ])
        
        if photo_file_id:
            await message.answer_photo(
                photo=photo_file_id,
                caption=profile_text,
                reply_markup=edit_keyboard
            )
        else:
            await message.answer(
                profile_text,
                reply_markup=edit_keyboard
            )
        
        logger.info(f"Пользователь {user.id} просмотрел свой профиль")
        
    except Exception as e:
        logger.error(f"Ошибка при показе профиля пользователя {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке профиля. Попробуйте позже.")


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "⚙️ Настройки".
    Показывает настройки пользователя (предпочтения по возрасту).
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста (добавлен UserContextMiddleware)
    """
    logger.info(f"Обработчик show_settings вызван для пользователя {message.from_user.id}")
    
    # Очищаем состояние FSM, если пользователь в процессе регистрации
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        logger.debug(f"Очищено состояние FSM для пользователя {message.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте и БД для настроек")
            return
    
    # Проверяем верификацию вручную
    if not user.is_verified:
        await message.answer("⏳ Ваша анкета находится на модерации.\n\nПожалуйста, дождитесь проверки модератором.")
        return
    
    try:
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await message.answer("❌ Ваш профиль не найден. Пожалуйста, завершите регистрацию.")
            return
        
        # Определяем статус фильтра по полу
        filter_status = "✅ Включен" if profile.filter_by_opposite_gender else "❌ Выключен"
        filter_description = ""
        if profile.filter_by_opposite_gender:
            if profile.gender == "Мужской":
                filter_description = "Показываются только девушки"
            elif profile.gender == "Женский":
                filter_description = "Показываются только парни"
            else:
                filter_description = "Фильтр активен"
        else:
            filter_description = "Показываются все"
        
        # Формируем текст настроек
        settings_text = (
            "⚙️ Настройки поиска\n\n"
            f"🔍 Возраст для поиска:\n"
            f"   От {profile.min_age_preference} до {profile.max_age_preference} лет\n\n"
            f"⚧️ Фильтр по полу: {filter_status}\n"
            f"   {filter_description}\n\n"
            "Используйте кнопки ниже для изменения настроек:"
        )
        
        # Создаем клавиатуру с кнопками изменения настроек
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔻 Минимальный возраст",
                    callback_data="settings:min_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔺 Максимальный возраст",
                    callback_data="settings:max_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⚧️ Фильтр по полу ({'✅' if profile.filter_by_opposite_gender else '❌'})",
                    callback_data="settings:toggle_gender_filter"
                )
            ]
        ])
        
        await message.answer(
            settings_text,
            reply_markup=keyboard
        )
        
        logger.info(f"Пользователь {user.id} открыл настройки")
        
    except Exception as e:
        logger.error(f"Ошибка при показе настроек пользователя {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке настроек. Попробуйте позже.")


@router.callback_query(F.data == "settings:min_age")
async def handle_min_age_settings(callback: CallbackQuery, state: FSMContext, user=None):
    """
    Обработчик кнопки "Минимальный возраст".
    Запрашивает ввод нового минимального возраста.
    """
    logger.info(f"Обработчик handle_min_age_settings вызван для пользователя {callback.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
    
    # Проверяем верификацию
    if not user.is_verified:
        await callback.answer("⏳ Ваша анкета находится на модерации.", show_alert=True)
        return
    
    try:
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return
        
        # Устанавливаем состояние для ввода минимального возраста
        await state.set_state(ProfileEditState.editing_min_age_preference)
        
        await callback.message.answer(
            f"🔽 Введите минимальный возраст для поиска (от 18 до {profile.max_age_preference} лет):\n\n"
            f"Текущее значение: {profile.min_age_preference} лет"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке настройки минимального возраста: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "settings:max_age")
async def handle_max_age_settings(callback: CallbackQuery, state: FSMContext, user=None):
    """
    Обработчик кнопки "Максимальный возраст".
    Запрашивает ввод нового максимального возраста.
    """
    logger.info(f"Обработчик handle_max_age_settings вызван для пользователя {callback.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
    
    # Проверяем верификацию
    if not user.is_verified:
        await callback.answer("⏳ Ваша анкета находится на модерации.", show_alert=True)
        return
    
    try:
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return
        
        # Устанавливаем состояние для ввода максимального возраста
        await state.set_state(ProfileEditState.editing_max_age_preference)
        
        await callback.message.answer(
            f"🔼 Введите максимальный возраст для поиска (от {profile.min_age_preference} до 100 лет):\n\n"
            f"Текущее значение: {profile.max_age_preference} лет"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке настройки максимального возраста: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(StateFilter(ProfileEditState.editing_min_age_preference))
async def process_min_age_preference(message: Message, state: FSMContext, user=None):
    """
    Обрабатывает ввод минимального возраста для поиска.
    """
    logger.info(f"Обработчик process_min_age_preference вызван для пользователя {message.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
    
    try:
        # Парсим возраст
        try:
            new_min_age = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Пожалуйста, введите число (например, 18):")
            return
        
        # Получаем профиль
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await message.answer("❌ Профиль не найден")
            await state.clear()
            return
        
        # Валидация
        if new_min_age < 18:
            await message.answer("❌ Минимальный возраст не может быть меньше 18 лет. Попробуйте еще раз:")
            return
        
        if new_min_age >= profile.max_age_preference:
            await message.answer(
                f"❌ Минимальный возраст должен быть меньше максимального ({profile.max_age_preference} лет). "
                f"Попробуйте еще раз:"
            )
            return
        
        # Обновляем профиль
        profile_repo.update(profile.id, min_age_preference=new_min_age)
        
        await message.answer(
            f"✅ Минимальный возраст для поиска изменен на {new_min_age} лет.\n\n"
            f"Теперь поиск будет показывать анкеты от {new_min_age} до {profile.max_age_preference} лет."
        )
        
        await state.clear()
        logger.info(f"Пользователь {user.id} изменил минимальный возраст на {new_min_age}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке минимального возраста: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обновлении настроек. Попробуйте позже.")
        await state.clear()


@router.callback_query(F.data == "settings:toggle_gender_filter")
async def handle_toggle_gender_filter(callback: CallbackQuery, user=None):
    """
    Обработчик кнопки переключения фильтра по полу.
    Переключает фильтр по противоположному полу.
    """
    logger.info(f"Обработчик handle_toggle_gender_filter вызван для пользователя {callback.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
    
    # Проверяем верификацию
    if not user.is_verified:
        await callback.answer("⏳ Ваша анкета находится на модерации.", show_alert=True)
        return
    
    try:
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return
        
        # Переключаем фильтр
        new_value = not profile.filter_by_opposite_gender
        profile_repo.update(profile.id, filter_by_opposite_gender=new_value)
        
        # Инвалидируем кэш кандидатов, так как фильтр изменился
        invalidate_user_cache(user.id)
        
        # Обновляем сообщение с новыми настройками
        filter_status = "✅ Включен" if new_value else "❌ Выключен"
        filter_description = ""
        if new_value:
            if profile.gender == "Мужской":
                filter_description = "Показываются только девушки"
            elif profile.gender == "Женский":
                filter_description = "Показываются только парни"
            else:
                filter_description = "Фильтр активен"
        else:
            filter_description = "Показываются все"
        
        settings_text = (
            "⚙️ Настройки поиска\n\n"
            f"🔍 Возраст для поиска:\n"
            f"   От {profile.min_age_preference} до {profile.max_age_preference} лет\n\n"
            f"⚧️ Фильтр по полу: {filter_status}\n"
            f"   {filter_description}\n\n"
            "Используйте кнопки ниже для изменения настроек:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔻 Минимальный возраст",
                    callback_data="settings:min_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔺 Максимальный возраст",
                    callback_data="settings:max_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⚧️ Фильтр по полу ({'✅' if new_value else '❌'})",
                    callback_data="settings:toggle_gender_filter"
                )
            ]
        ])
        
        try:
            await callback.message.edit_text(
                settings_text,
                reply_markup=keyboard
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                settings_text,
                reply_markup=keyboard
            )
        
        await callback.answer(
            f"✅ Фильтр по полу {'включен' if new_value else 'выключен'}"
        )
        logger.info(f"Пользователь {user.id} {'включил' if new_value else 'выключил'} фильтр по полу")
        
    except Exception as e:
        logger.error(f"Ошибка при переключении фильтра по полу: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(StateFilter(ProfileEditState.editing_max_age_preference))
async def process_max_age_preference(message: Message, state: FSMContext, user=None):
    """
    Обрабатывает ввод максимального возраста для поиска.
    """
    logger.info(f"Обработчик process_max_age_preference вызван для пользователя {message.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
    
    try:
        # Парсим возраст
        try:
            new_max_age = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Пожалуйста, введите число (например, 100):")
            return
        
        # Получаем профиль
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await message.answer("❌ Профиль не найден")
            await state.clear()
            return
        
        # Валидация
        if new_max_age > 100:
            await message.answer("❌ Максимальный возраст не может быть больше 100 лет. Попробуйте еще раз:")
            return
        
        if new_max_age <= profile.min_age_preference:
            await message.answer(
                f"❌ Максимальный возраст должен быть больше минимального ({profile.min_age_preference} лет). "
                f"Попробуйте еще раз:"
            )
            return
        
        # Обновляем профиль
        profile_repo.update(profile.id, max_age_preference=new_max_age)
        
        await message.answer(
            f"✅ Максимальный возраст для поиска изменен на {new_max_age} лет.\n\n"
            f"Теперь поиск будет показывать анкеты от {profile.min_age_preference} до {new_max_age} лет."
        )
        
        await state.clear()
        logger.info(f"Пользователь {user.id} изменил максимальный возраст на {new_max_age}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке максимального возраста: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обновлении настроек. Попробуйте позже.")
        await state.clear()


# ========== Обработчики редактирования профиля ==========

@router.callback_query(F.data == "edit_profile")
async def handle_edit_profile(callback: CallbackQuery, user=None):
    """
    Обработчик кнопки "Редактировать анкету".
    Показывает меню редактирования профиля.
    """
    logger.info(f"Обработчик handle_edit_profile вызван для пользователя {callback.from_user.id}")
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
    
    # Проверяем верификацию
    if not user.is_verified:
        await callback.answer("⏳ Ваша анкета находится на модерации.", show_alert=True)
        return
    
    try:
        profile = profile_repo.get_by_user_id(user.id)
        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return
        
        # Создаем клавиатуру с кнопками редактирования
        edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Имя",
                    callback_data="edit:name"
                ),
                InlineKeyboardButton(
                    text="🎂 Возраст",
                    callback_data="edit:age"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚧️ Пол",
                    callback_data="edit:gender"
                ),
                InlineKeyboardButton(
                    text="📍 Город",
                    callback_data="edit:city"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Описание",
                    callback_data="edit:bio"
                ),
                InlineKeyboardButton(
                    text="📷 Фото",
                    callback_data="edit:photo"
                )
            ]
        ])
        
        # Пытаемся отредактировать caption (если есть фото) или текст
        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=(
                        "✏️ Редактирование анкеты\n\n"
                        "Выберите, что хотите изменить:"
                    ),
                    reply_markup=edit_keyboard
                )
            else:
                await callback.message.edit_text(
                    "✏️ Редактирование анкеты\n\n"
                    "Выберите, что хотите изменить:",
                    reply_markup=edit_keyboard
                )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                "✏️ Редактирование анкеты\n\n"
                "Выберите, что хотите изменить:",
                reply_markup=edit_keyboard
            )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при показе меню редактирования: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "edit:name")
async def handle_edit_name(callback: CallbackQuery, state: FSMContext, user=None):
    """Обработчик редактирования имени."""
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    profile = profile_repo.get_by_user_id(user.id)
    await state.set_state(ProfileEditState.editing_name)
    await callback.message.answer(
        f"✏️ Введите новое имя:\n\nТекущее имя: {profile.name}"
    )
    await callback.answer()


@router.callback_query(F.data == "edit:age")
async def handle_edit_age(callback: CallbackQuery, state: FSMContext, user=None):
    """Обработчик редактирования возраста."""
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    profile = profile_repo.get_by_user_id(user.id)
    # Получаем минимальный возраст из настроек БД
    min_age = SettingsRepository.get_int("min_age", MIN_AGE_DEFAULT)
    await state.set_state(ProfileEditState.editing_age)
    await callback.message.answer(
        f"🎂 Введите новый возраст (от {min_age} до 120 лет):\n\nТекущий возраст: {profile.age} лет"
    )
    await callback.answer()


@router.callback_query(F.data == "edit:gender")
async def handle_edit_gender(callback: CallbackQuery, state: FSMContext, user=None):
    """Обработчик редактирования пола."""
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    profile = profile_repo.get_by_user_id(user.id)
    await state.set_state(ProfileEditState.editing_gender)
    await callback.message.answer(
        f"⚧️ Выберите пол:\n\nТекущий пол: {profile.gender}",
        reply_markup=get_gender_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "edit:city")
async def handle_edit_city(callback: CallbackQuery, state: FSMContext, user=None):
    """Обработчик редактирования города."""
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    profile = profile_repo.get_by_user_id(user.id)
    await state.set_state(ProfileEditState.editing_city)
    current_city = profile.city if profile.city else "не указан"
    await callback.message.answer(
        f"📍 Введите новый город (или /skip чтобы удалить):\n\nТекущий город: {current_city}"
    )
    await callback.answer()


@router.callback_query(F.data == "edit:bio")
async def handle_edit_bio(callback: CallbackQuery, state: FSMContext, user=None):
    """Обработчик редактирования описания."""
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    profile = profile_repo.get_by_user_id(user.id)
    await state.set_state(ProfileEditState.editing_bio)
    current_bio = profile.bio if profile.bio else "не указано"
    await callback.message.answer(
        f"📝 Введите новое описание (или /skip чтобы удалить):\n\nТекущее описание: {current_bio}"
    )
    await callback.answer()


@router.callback_query(F.data == "edit:photo")
async def handle_edit_photo(callback: CallbackQuery, state: FSMContext, user=None):
    """Обработчик редактирования фото."""
    if not user:
        user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    await state.set_state(ProfileEditState.editing_photo)
    await callback.message.answer(
        "📷 Отправьте новое фото для анкеты:"
    )
    await callback.answer()


# Обработчики ввода новых значений

@router.message(StateFilter(ProfileEditState.editing_name))
async def process_edit_name(message: Message, state: FSMContext, user=None):
    """Обрабатывает ввод нового имени."""
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
    
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.answer("❌ Имя должно содержать минимум 2 символа. Попробуйте еще раз:")
        return
    
    profile = profile_repo.get_by_user_id(user.id)
    profile_repo.update(profile.id, name=name)
    await message.answer(f"✅ Имя изменено на: {name}")
    await state.clear()
    logger.info(f"Пользователь {user.id} изменил имя на {name}")


@router.message(StateFilter(ProfileEditState.editing_age))
async def process_edit_age(message: Message, state: FSMContext, user=None):
    """Обрабатывает ввод нового возраста."""
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
    
    # Получаем минимальный возраст из настроек БД
    min_age = SettingsRepository.get_int("min_age", MIN_AGE_DEFAULT)
    
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Пожалуйста, введите возраст числом (например, 25):")
        return
    
    if age < min_age or age > 120:
        await message.answer(
            f"❌ Возраст должен быть от {min_age} до 120 лет. Попробуйте еще раз:"
        )
        return
    
    profile = profile_repo.get_by_user_id(user.id)
    profile_repo.update(profile.id, age=age)
    await message.answer(f"✅ Возраст изменен на: {age} лет")
    await state.clear()
    logger.info(f"Пользователь {user.id} изменил возраст на {age}")


@router.message(StateFilter(ProfileEditState.editing_gender))
async def process_edit_gender(message: Message, state: FSMContext, user=None):
    """Обрабатывает выбор нового пола."""
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
    
    from aiogram.types import ReplyKeyboardRemove
    
    gender_text = message.text.strip()
    valid_genders = ["Мужской", "Женский", "Другой"]
    
    if gender_text not in valid_genders:
        await message.answer(
            "❌ Пожалуйста, выберите пол из предложенных вариантов:",
            reply_markup=get_gender_keyboard()
        )
        return
    
    profile = profile_repo.get_by_user_id(user.id)
    profile_repo.update(profile.id, gender=gender_text)
    await message.answer(f"✅ Пол изменен на: {gender_text}")
    await state.clear()
    logger.info(f"Пользователь {user.id} изменил пол на {gender_text}")


@router.message(StateFilter(ProfileEditState.editing_city))
async def process_edit_city(message: Message, state: FSMContext, user=None):
    """Обрабатывает ввод нового города."""
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
    
    from aiogram.types import ReplyKeyboardRemove
    
    # Проверка на команду /skip
    if message.text and message.text.strip() == "/skip":
        profile = profile_repo.get_by_user_id(user.id)
        profile_repo.update(profile.id, city=None)
        await message.answer("✅ Город удален")
        await state.clear()
        logger.info(f"Пользователь {user.id} удалил город")
        return
    
    city = message.text.strip() if message.text else None
    if city and len(city) < 2:
        await message.answer("❌ Название города должно содержать минимум 2 символа. Попробуйте еще раз:")
        return
    
    profile = profile_repo.get_by_user_id(user.id)
    profile_repo.update(profile.id, city=city if city else None)
    city_text = city if city else "удален"
    await message.answer(f"✅ Город изменен на: {city_text}")
    await state.clear()
    logger.info(f"Пользователь {user.id} изменил город на {city_text}")


@router.message(StateFilter(ProfileEditState.editing_bio))
async def process_edit_bio(message: Message, state: FSMContext, user=None):
    """Обрабатывает ввод нового описания."""
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
    
    from aiogram.types import ReplyKeyboardRemove
    
    # Проверка на команду /skip
    if message.text and message.text.strip() == "/skip":
        profile = profile_repo.get_by_user_id(user.id)
        profile_repo.update(profile.id, bio=None)
        await message.answer("✅ Описание удалено")
        await state.clear()
        logger.info(f"Пользователь {user.id} удалил описание")
        return
    
    bio = message.text.strip() if message.text else None
    if bio and len(bio) > 1000:
        await message.answer("❌ Описание не должно превышать 1000 символов. Попробуйте еще раз:")
        return
    
    profile = profile_repo.get_by_user_id(user.id)
    
    # Проверка через ИИ перед сохранением
    from services.ai_profile_checker import AIProfileChecker
    from keyboards.inline.moderation_keyboard import get_ai_moderation_keyboard
    
    bot = get_bot()
    ai_checker = AIProfileChecker(bot)
    
    # Уведомляем пользователя о проверке
    checking_message = await message.answer("🤖 Наш AI-агент проверяет ваше описание...")
    
    # Проверяем описание через ИИ
    ai_result = None
    if bio:
        ai_result = await ai_checker.check_profile_content(
            user_id=user.id,
            field_type="bio",
            content=bio
        )
    
    # Удаляем сообщение о проверке
    try:
        await checking_message.delete()
    except Exception:
        pass
    
    if ai_result:
        # Найдены нарушения - обрабатываем результат
        check_type = "general"
        if ai_result.detected_issues:
            if "nudity" in ai_result.detected_issues:
                check_type = "nudity"
            elif "violence" in ai_result.detected_issues:
                check_type = "violence"
            elif "drugs" in ai_result.detected_issues:
                check_type = "drugs"
            else:
                check_type = ai_result.detected_issues[0] if ai_result.detected_issues else "general"
        
        # Обрабатываем результат проверки
        action_result = await ai_checker.handle_ai_moderation_result(
            user_id=user.id,
            result=ai_result,
            field_type="bio",
            check_type=check_type
        )
        
        # Сохраняем описание перед отправкой админам
        profile_repo.update(profile.id, bio=bio if bio else None)
        logger.info(f"Описание сохранено для отправки админам (пользователь {user.id})")
        
        # Если пользователь был забанен автоматически, отправляем сообщение
        if action_result['action'] == 'ban' and action_result.get('message'):
            await message.answer(action_result['message'])
            await state.clear()
            logger.warning(f"Пользователь {user.id} забанен автоматически при редактировании описания")
            # Продолжаем отправку админам даже после бана
        
        # Уведомляем админов, если нужно
        if action_result['should_notify_admin'] and config.ADMIN_GROUP_ID:
            try:
                # Отправляем краткое уведомление, если есть нарушения
                if action_result['should_notify_admin']:
                    notification = ai_checker.format_admin_notification(
                        user_id=user.id,
                        result=ai_result,
                        check_type=check_type,
                        field_type="bio",
                        auto_banned=action_result.get('auto_banned', False)
                    )
                    
                    keyboard = get_ai_moderation_keyboard(user.id, check_type)
                    
                    await bot.send_message(
                        chat_id=config.ADMIN_GROUP_ID,
                        text=notification,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    logger.info(f"Уведомление о нарушении отправлено админам для пользователя {user.id}")
                
                # Отправляем полную анкету с информацией о решении ИИ
                success = await ai_checker.send_profile_to_admins(
                    user_id=user.id,
                    result=ai_result,
                    check_type=check_type,
                    field_type="bio",
                    auto_banned=action_result.get('auto_banned', False)
                )
                if success:
                    logger.info(f"Анкета пользователя {user.id} отправлена админам (с решением ИИ)")
                else:
                    logger.error(f"Не удалось отправить анкету пользователя {user.id} админам")
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления админам: {e}", exc_info=True)
        
        # Если не было автоматического бана, но есть нарушения - сообщаем пользователю
        if action_result['action'] == 'notify':
            await message.answer(
                "⚠️ Описание отправлено на дополнительную проверку модератором. "
                "Вы получите уведомление после проверки."
            )
            await state.clear()
            return
        
        # Если был автоматический бан, уже отправили сообщение выше
        if action_result['action'] == 'ban':
            return
    
    # Если проверка прошла успешно или ИИ недоступен - сохраняем описание
    profile_repo.update(profile.id, bio=bio if bio else None)
    
    # Всегда отправляем обновленную анкету в группу админов
    if config.ADMIN_GROUP_ID:
        try:
            if ai_result:
                # Уже отправили выше
                pass
            else:
                # ИИ не нашел нарушений или недоступен - отправляем анкету без информации о нарушениях
                success = await ai_checker.send_profile_to_admins_safe(
                    user_id=user.id,
                    field_type="bio"
                )
                if success:
                    logger.info(f"Анкета пользователя {user.id} отправлена админам (без нарушений)")
                else:
                    logger.error(f"Не удалось отправить анкету пользователя {user.id} админам")
        except Exception as e:
            logger.error(f"Ошибка при отправке анкеты админам: {e}", exc_info=True)
    
    await message.answer(f"✅ Описание изменено")
    await state.clear()
    logger.info(f"Пользователь {user.id} изменил описание")


@router.message(StateFilter(ProfileEditState.editing_photo), F.photo)
async def process_edit_photo(message: Message, state: FSMContext, user=None):
    """Обрабатывает загрузку нового фото."""
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
    
    try:
        # Получаем самое большое фото
        photo = message.photo[-1]
        photo_file_id = photo.file_id
        
        profile = profile_repo.get_by_user_id(user.id)
        
        # Проверка через ИИ перед сохранением
        from services.ai_profile_checker import AIProfileChecker
        from keyboards.inline.moderation_keyboard import get_ai_moderation_keyboard
        
        bot = get_bot()
        ai_checker = AIProfileChecker(bot)
        
        # Уведомляем пользователя о проверке
        checking_message = await message.answer("🤖 Наш AI-агент проверяет ваше фото...")
        
        # Проверяем фото через ИИ
        ai_result = await ai_checker.check_profile_content(
            user_id=user.id,
            field_type="photo",
            photo_file_id=photo_file_id
        )
        
        # Удаляем сообщение о проверке
        try:
            await checking_message.delete()
        except Exception:
            pass
        
        # Сохраняем фото перед отправкой админам (чтобы они видели обновленную анкету)
        from database.repositories.profile_repo import ProfileRepository
        ProfileRepository.add_media(
            profile_id=profile.id,
            photo_file_id=photo_file_id,
            is_main=True
        )
        logger.info(f"Фото сохранено (пользователь {user.id})")
        
        # Всегда отправляем обновленную анкету в группу админов
        if config.ADMIN_GROUP_ID:
            try:
                if ai_result:
                    # Найдены нарушения - обрабатываем результат
                    # Определяем тип нарушения из detected_issues (сохранен в check_profile_content)
                    check_type = "general"
                    if ai_result.detected_issues:
                        # Ищем сохраненный тип нарушения
                        violation_types = [issue.split(":")[1] for issue in ai_result.detected_issues if issue.startswith("violation_type:")]
                        if violation_types:
                            check_type = violation_types[0]
                        elif any("nudity" in issue.lower() or "nsfw" in issue.lower() for issue in ai_result.detected_issues):
                            check_type = "nudity"
                        elif any("drug" in issue.lower() for issue in ai_result.detected_issues):
                            check_type = "drugs"
                        elif any("violence" in issue.lower() or "weapon" in issue.lower() for issue in ai_result.detected_issues):
                            check_type = "violence"
                    
                    # Обрабатываем результат проверки
                    action_result = await ai_checker.handle_ai_moderation_result(
                        user_id=user.id,
                        result=ai_result,
                        field_type="photo",
                        check_type=check_type
                    )
                    
                    # Если пользователь был забанен автоматически, отправляем сообщение
                    if action_result['action'] == 'ban' and action_result.get('message'):
                        await message.answer(action_result['message'])
                        await state.clear()
                        logger.warning(f"Пользователь {user.id} забанен автоматически при редактировании фото")
                        # Продолжаем отправку админам даже после бана
                    
                    # Отправляем краткое уведомление, если есть нарушения
                    if action_result['should_notify_admin']:
                        notification = ai_checker.format_admin_notification(
                            user_id=user.id,
                            result=ai_result,
                            check_type=check_type,
                            field_type="photo",
                            auto_banned=action_result.get('auto_banned', False)
                        )
                        
                        keyboard = get_ai_moderation_keyboard(user.id, check_type)
                        
                        await bot.send_message(
                            chat_id=config.ADMIN_GROUP_ID,
                            text=notification,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        logger.info(f"Уведомление о нарушении отправлено админам для пользователя {user.id}")
                    
                    # Отправляем полную анкету с информацией о решении ИИ
                    success = await ai_checker.send_profile_to_admins(
                        user_id=user.id,
                        result=ai_result,
                        check_type=check_type,
                        field_type="photo",
                        auto_banned=action_result.get('auto_banned', False)
                    )
                    if success:
                        logger.info(f"Анкета пользователя {user.id} отправлена админам (с решением ИИ)")
                    else:
                        logger.error(f"Не удалось отправить анкету пользователя {user.id} админам")
                    
                    # Если не было автоматического бана, но есть нарушения - сообщаем пользователю
                    if action_result['action'] == 'notify':
                        await message.answer(
                            "⚠️ Фото отправлено на дополнительную проверку модератором. "
                            "Вы получите уведомление после проверки."
                        )
                        await state.clear()
                        return
                    
                    # Если был автоматический бан, уже отправили сообщение выше
                    if action_result['action'] == 'ban':
                        return
                else:
                    # ИИ не нашел нарушений или недоступен - отправляем анкету без информации о нарушениях
                    success = await ai_checker.send_profile_to_admins_safe(
                        user_id=user.id,
                        field_type="photo"
                    )
                    if success:
                        logger.info(f"Анкета пользователя {user.id} отправлена админам (без нарушений)")
                    else:
                        logger.error(f"Не удалось отправить анкету пользователя {user.id} админам")
                        
            except Exception as e:
                logger.error(f"Ошибка при отправке анкеты админам: {e}", exc_info=True)
        
        # Если проверка прошла успешно или ИИ недоступен - сообщаем пользователю
        await message.answer("✅ Фото обновлено!")
        await state.clear()
        logger.info(f"Пользователь {user.id} обновил фото")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении фото: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обновлении фото. Попробуйте позже.")
        await state.clear()
