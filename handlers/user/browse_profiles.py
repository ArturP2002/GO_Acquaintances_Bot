"""
Обработчики просмотра анкет.
Показ анкет пользователям с возможностью лайка, пропуска, возврата назад и жалобы.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.matching_service import MatchingService
from database.repositories.profile_repo import ProfileRepository
from database.repositories.user_repo import UserRepository
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
from keyboards.inline.profile_keyboard import get_profile_keyboard, get_next_profile_keyboard
from keyboards.reply.profile_keyboard import get_profile_reply_keyboard
from states.browsing_state import BrowsingState
from filters.is_verified import IsVerified
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для просмотра анкет
router = Router()

# Инициализация репозиториев и сервисов
profile_repo = ProfileRepository()
user_repo = UserRepository()
matching_service = MatchingService()


async def show_next_profile_message(message: Message, user_id: int, state: FSMContext):
    """
    Показывает следующую анкету пользователю через message.
    Используется как внутренняя функция для показа анкет с reply-кнопками.
    
    Args:
        message: Message объект для ответа
        user_id: ID пользователя в БД (не telegram_id)
        state: FSM контекст для отслеживания текущего профиля
    """
    try:
        # Получаем профиль текущего пользователя для получения предпочтений по возрасту
        user_profile = profile_repo.get_by_user_id(user_id)
        if not user_profile:
            await message.answer("❌ Ваш профиль не найден")
            logger.error(f"Профиль пользователя {user_id} не найден")
            return
        
        # Получаем предпочтения по возрасту из профиля пользователя
        min_age = user_profile.min_age_preference
        max_age = user_profile.max_age_preference
        
        # Получаем следующую анкету через matching service
        next_profile = matching_service.get_next_profile(
            user_id=user_id,
            min_age=min_age,
            max_age=max_age
        )
        
        # Если анкет нет (включая просмотренные) - все анкеты просмотрены дважды
        if not next_profile:
            await state.clear()
            # Отправляем сообщение пользователю, что все анкеты закончились
            from keyboards.reply.main_menu import get_main_menu_keyboard
            await message.answer(
                "😔 К сожалению, вы просмотрели все доступные анкеты.\n\n"
                "Попробуйте позже или измените настройки поиска в вашем профиле.",
                reply_markup=get_main_menu_keyboard()
            )
            logger.info(f"Пользователь {user_id} просмотрел все доступные анкеты (включая повторный круг)")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(next_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(next_profile)
        
        # Получаем user_id профиля (не profile.id, а user_id)
        profile_user_id = next_profile.user_id
        
        # Создаем reply-клавиатуру с кнопками
        keyboard = get_profile_reply_keyboard()
        
        # Записываем просмотр в ProfileViews
        profile_repo.add_view(viewer_id=user_id, profile_id=next_profile.id)
        logger.debug(f"Просмотр анкеты {next_profile.id} пользователем {user_id} записан")
        
        # Добавляем профиль в историю для кнопки "Назад"
        profile_repo.add_to_history(user_id=user_id, profile_id=next_profile.id)
        logger.debug(f"Анкета {next_profile.id} добавлена в историю для пользователя {user_id}")
        
        # Сохраняем текущий профиль в FSM state
        await state.set_state(BrowsingState.viewing_profile)
        await state.update_data(
            current_profile_id=next_profile.id,
            current_profile_user_id=profile_user_id
        )
        
        # Отправляем новое сообщение с анкетой
        if photo_file_id:
            await message.answer_photo(
                photo=photo_file_id,
                caption=profile_text,
                reply_markup=keyboard
            )
        else:
            await message.answer(
                text=profile_text,
                reply_markup=keyboard
            )
        
        # Показываем случайное предложение пригласить друга (10% вероятность)
        try:
            from services.referral_service import ReferralService
            bot = get_bot()
            referral_service = ReferralService(bot)
            user = user_repo.get_by_id(user_id)
            if user:
                # Вызываем асинхронно, не блокируя основной поток
                await referral_service.show_random_referral_suggestion(user.telegram_id)
        except Exception as e:
            # Игнорируем ошибки при показе предложения реферала
            logger.debug(f"Не удалось показать предложение реферала: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при показе анкеты для пользователя {user_id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке анкеты")


async def show_next_profile(callback: CallbackQuery, user_id: int):
    """
    Обёртка для совместимости со старым кодом.
    Показывает следующую анкету через CallbackQuery.
    
    Args:
        callback: CallbackQuery объект
        user_id: ID пользователя в БД (не telegram_id)
    """
    from aiogram.fsm.context import FSMContext
    from loader import get_dispatcher
    
    try:
        # Получаем storage из диспетчера, чтобы состояние сохранялось
        dispatcher = get_dispatcher()
        storage = getattr(dispatcher, 'storage', None)
        
        if storage is None:
            # Если storage не установлен, создаем временный MemoryStorage
            from aiogram.fsm.storage.memory import MemoryStorage
            storage = MemoryStorage()
    except Exception:
        # Если не удалось получить dispatcher, используем временный storage
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
    
    # Создаем ключ для FSM context используя resolve_address
    key = storage.resolve_address(
        chat=callback.message.chat.id,
        user=callback.message.from_user.id
    )
    
    # Создаем FSM context
    state = FSMContext(storage=storage, key=key)
    
    # Вызываем основную функцию с message из callback
    await show_next_profile_message(callback.message, user_id, state)
    
    # Отвечаем на callback, чтобы убрать индикатор загрузки
    try:
        await callback.answer()
    except Exception:
        # Если callback уже был обработан, игнорируем ошибку
        pass


async def show_previous_profile_message(message: Message, user_id: int, state: FSMContext):
    """
    Показывает предыдущую анкету из истории просмотров через message.
    
    Args:
        message: Message объект для ответа
        user_id: ID пользователя в БД (не telegram_id)
        state: FSM контекст для отслеживания текущего профиля
    """
    try:
        # Получаем максимальную позицию в истории
        max_position = profile_repo.get_current_position(user_id)
        
        # Если позиция <= 0, значит это первая анкета или истории нет
        if max_position <= 0:
            await message.answer("Это первая анкета в истории")
            return
        
        # Получаем все записи истории для пользователя, отсортированные по позиции (от большей к меньшей)
        from database.models.like import ProfileHistory
        from database.models.user import User
        
        # Получаем все записи истории, отсортированные по позиции (от большей к меньшей)
        all_history = list(ProfileHistory.select().where(
            ProfileHistory.user_id == user_id
        ).order_by(ProfileHistory.position.desc()))
        
        if not all_history:
            await message.answer("В истории нет анкет")
            return
        
        # Находим текущий профиль - это самый последний (с максимальной позицией)
        # Но нужно проверить, не забанен ли он
        current_profile = None
        current_position = None
        
        # Ищем первый незабаненный профиль с максимальной позицией (текущий)
        for history_entry in all_history:
            try:
                candidate_profile = history_entry.profile
                profile_user = User.get_by_id(candidate_profile.user_id)
                if not profile_user.is_banned:
                    current_profile = candidate_profile
                    current_position = history_entry.position
                    break
            except (User.DoesNotExist, AttributeError):
                continue
        
        # Если не нашли текущий профиль, значит все забанены
        if current_profile is None or current_position is None:
            await message.answer("В истории нет доступных анкет")
            return
        
        # Если текущая позиция <= 0, значит это первая анкета
        if current_position <= 0:
            await message.answer("Это первая анкета в истории")
            return
        
        # Ищем предыдущий незабаненный профиль
        previous_profile = None
        previous_position = current_position - 1
        
        # Ищем первый незабаненный профиль в истории, начиная с предыдущей позиции
        while previous_position >= 0:
            try:
                history_entry = ProfileHistory.get(
                    (ProfileHistory.user_id == user_id) &
                    (ProfileHistory.position == previous_position)
                )
                candidate_profile = history_entry.profile
                
                # Проверяем, не забанен ли пользователь этого профиля
                profile_user = User.get_by_id(candidate_profile.user_id)
                if not profile_user.is_banned:
                    previous_profile = candidate_profile
                    break
                
                # Если забанен, ищем дальше назад
                previous_position -= 1
            except (ProfileHistory.DoesNotExist, User.DoesNotExist, AttributeError):
                # Если запись не найдена, ищем дальше назад
                previous_position -= 1
        
        # Если не нашли незабаненного профиля в истории
        if previous_profile is None:
            await message.answer("В истории нет доступных анкет")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(previous_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(previous_profile)
        
        # Получаем user_id профиля
        profile_user_id = previous_profile.user_id
        
        # Создаем reply-клавиатуру с кнопками
        keyboard = get_profile_reply_keyboard()
        
        # Сохраняем текущий профиль в FSM state
        await state.set_state(BrowsingState.viewing_profile)
        await state.update_data(
            current_profile_id=previous_profile.id,
            current_profile_user_id=profile_user_id
        )
        
        # Отправляем новое сообщение с анкетой
        if photo_file_id:
            await message.answer_photo(
                photo=photo_file_id,
                caption=profile_text,
                reply_markup=keyboard
            )
        else:
            await message.answer(
                text=profile_text,
                reply_markup=keyboard
            )
        
        logger.debug(f"Показана предыдущая анкета {previous_profile.id} пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при показе предыдущей анкеты для пользователя {user_id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке предыдущей анкеты")


@router.message(F.text == "❤️", BrowsingState.viewing_profile)
async def handle_like_profile(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "❤️ Лайк".
    Обрабатывает лайк текущего профиля и показывает следующую анкету.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await message.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.")
        await state.clear()
        return
    
    try:
        # Получаем текущий профиль из FSM state
        data = await state.get_data()
        current_profile_user_id = data.get("current_profile_user_id")
        
        if not current_profile_user_id:
            await message.answer("❌ Не удалось определить текущий профиль. Попробуйте начать просмотр заново.")
            await state.clear()
            return
        
        target_user_id = current_profile_user_id
        
        logger.info(f"Обработка лайка: пользователь {user.id} (telegram_id={user.telegram_id}) лайкает пользователя {target_user_id}")
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис лайков
        from services.like_service import LikeService
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
            await message.answer(error_message or "Ошибка при добавлении лайка")
            logger.warning(f"Не удалось добавить лайк от {user.id} к {target_user_id}: {error_message}")
            return
        
        # Если есть мэтч - создаем его и уведомляем пользователей
        if has_match:
            try:
                await like_service.create_match(user.id, target_user_id)
                logger.info(f"Создан мэтч между пользователями {user.id} и {target_user_id}")
                
                # Показываем уведомление о мэтче
                await message.answer("🎉 У вас взаимная симпатия!")
            except Exception as e:
                logger.error(f"Ошибка при создании мэтча между {user.id} и {target_user_id}: {e}", exc_info=True)
                # Продолжаем выполнение даже если не удалось создать мэтч
        else:
            # Просто подтверждаем лайк
            await message.answer("❤️ Лайк поставлен!")
            
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
        await show_next_profile_message(message, user.id, state)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке лайка для пользователя {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке лайка")


@router.message(F.text == "🚨", BrowsingState.viewing_profile)
async def handle_complaint_profile(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "🚨 Жалоба".
    Начинает процесс создания жалобы через FSM.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте для жалобы")
            return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await message.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.")
        await state.clear()
        return
    
    try:
        # Получаем текущий профиль из FSM state
        data = await state.get_data()
        current_profile_user_id = data.get("current_profile_user_id")
        
        if not current_profile_user_id:
            await message.answer("❌ Не удалось определить текущий профиль. Попробуйте начать просмотр заново.")
            await state.clear()
            return
        
        reported_user_id = current_profile_user_id
        
        # Проверка, что пользователь не жалуется на себя
        if reported_user_id == user.id:
            await message.answer("❌ Вы не можете пожаловаться на себя")
            return
        
        # Импортируем ComplaintState для перехода в состояние жалобы
        from states.complaint_state import ComplaintState
        from keyboards.inline.complaint_keyboard import get_complaint_reason_keyboard
        
        # Сохраняем reported_user_id в состоянии
        await state.update_data(reported_user_id=reported_user_id)
        
        # Переходим в состояние выбора причины жалобы
        await state.set_state(ComplaintState.waiting_for_reason)
        
        # Показываем клавиатуру с причинами жалоб
        await message.answer(
            "🚨 <b>Подача жалобы</b>\n\n"
            "Выберите причину жалобы:",
            parse_mode="HTML",
            reply_markup=get_complaint_reason_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при начале создания жалобы для пользователя {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при создании жалобы")
        await state.clear()


@router.message(F.text == "👎", BrowsingState.viewing_profile)
async def handle_skip_profile(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "👎 Пропустить".
    Пропускает текущую анкету и показывает следующую.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await message.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.")
        await state.clear()
        return
    
    # Просто показываем следующую анкету
    await show_next_profile_message(message, user.id, state)


@router.message(F.text == "↩", BrowsingState.viewing_profile)
async def handle_back_profile(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "↩ Назад".
    Показывает предыдущую анкету из истории просмотров.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте для кнопки назад")
            return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await message.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.")
        await state.clear()
        return
    
    await show_previous_profile_message(message, user.id, state)


@router.message(F.text == "💕 Смотреть анкеты")
async def handle_start_browsing(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "💕 Смотреть анкеты" из главного меню.
    Начинает просмотр анкет, показывая первую анкету.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте и БД для команды просмотра анкет")
            return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await message.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.")
        return
    
    await show_next_profile_message(message, user.id, state)


@router.message(F.text == "💤", BrowsingState.viewing_profile)
async def handle_back_to_main_menu(message: Message, state: FSMContext, user=None):
    """
    Обработчик кнопки "💤" для возврата в главное меню.
    Аналогичен команде /start - возвращает пользователя в главное меню.
    
    Args:
        message: Message объект
        state: FSM контекст
        user: Пользователь из контекста
    """
    # Очищаем состояние FSM
    await state.clear()
    
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте и БД для возврата в главное меню")
            return
    
    # Обновление времени последней активности
    user_repo.update_last_active(user.id)
    
    # Обновление username, если он изменился
    username = message.from_user.username
    if user.username != username:
        user.username = username
        user.save()
    
    # Проверка, является ли пользователь администратором
    from utils.admin_roles import get_user_role
    from core.constants import AdminRole
    from keyboards.inline.admin_keyboard import get_admin_main_keyboard
    
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
        logger.info(f"Администратор {message.from_user.id} (роль: {user_role}) открыл панель через кнопку 💤")
        return
    
    # Проверяем, забанен ли пользователь (только для не-администраторов)
    if not is_admin and user.is_banned:
        await message.answer(
            "🚫 Вы были заблокированы. Обратитесь к администратору."
        )
        logger.info(f"Забаненный пользователь {message.from_user.id} попытался вернуться в меню")
        return
    
    profile = profile_repo.get_by_user_id(user.id)
    
    if profile:
        # Проверяем, прошел ли пользователь модерацию
        if user.is_verified:
            # Пользователь зарегистрирован и верифицирован - показываем главное меню
            from keyboards.reply.main_menu import get_main_menu_keyboard
            await message.answer(
                "👋 Добро пожаловать обратно!\n\n"
                "Выберите действие из меню:",
                reply_markup=get_main_menu_keyboard()
            )
            logger.info(f"Пользователь {message.from_user.id} вернулся в главное меню через кнопку 💤")
        else:
            # Пользователь зарегистрирован, но не прошел модерацию
            await message.answer(
                "⏳ Ваша анкета находится на модерации.\n\n"
                "Пожалуйста, дождитесь проверки модератором. "
                "Вы получите уведомление, когда ваша анкета будет одобрена."
            )
            logger.info(f"Пользователь {message.from_user.id} вернулся в меню (зарегистрирован, но не верифицирован)")
    else:
        # Пользователь не зарегистрирован - предлагаем регистрацию
        from keyboards.reply.main_menu import get_registration_menu_keyboard
        welcome_text = (
            "👋 Привет! Добро пожаловать в бот знакомств!\n\n"
            "Здесь ты сможешь найти интересных людей и завести новые знакомства.\n\n"
            "Для начала работы нужно пройти регистрацию. Следуй инструкциям бота!"
        )
        
        await message.answer(
            welcome_text,
            reply_markup=get_registration_menu_keyboard()
        )
        logger.info(f"Пользователь {message.from_user.id} вернулся в меню (не зарегистрирован)")
