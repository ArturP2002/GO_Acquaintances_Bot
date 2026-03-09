"""
Обработчики просмотра анкет.
Показ анкет пользователям с возможностью лайка, пропуска, возврата назад и жалобы.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

from services.matching_service import MatchingService
from database.repositories.profile_repo import ProfileRepository
from database.repositories.user_repo import UserRepository
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
from keyboards.inline.profile_keyboard import get_profile_keyboard, get_next_profile_keyboard
from filters.is_verified import IsVerified
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для просмотра анкет
router = Router()

# Инициализация репозиториев и сервисов
profile_repo = ProfileRepository()
user_repo = UserRepository()
matching_service = MatchingService()


async def safe_edit_text(callback: CallbackQuery, text: str, reply_markup=None, user_id: int = None):
    """
    Безопасно редактирует текстовое сообщение, обрабатывая исключение "message is not modified".
    
    Args:
        callback: CallbackQuery объект
        text: Новый текст сообщения
        reply_markup: Клавиатура (опционально)
        user_id: ID пользователя для логирования (опционально)
    """
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup
        )
    except TelegramBadRequest as e:
        # Если сообщение не изменилось, это не критическая ошибка
        if "message is not modified" in str(e).lower():
            logger.debug(f"Текстовое сообщение не изменилось для пользователя {user_id}, пропускаем")
            await callback.answer()
            return True  # Успешно обработано
        # Для других ошибок пробрасываем исключение
        raise
    return False  # Сообщение было отредактировано


async def safe_edit_caption(callback: CallbackQuery, caption: str, reply_markup=None, user_id: int = None):
    """
    Безопасно редактирует подпись к фото, обрабатывая исключение "message is not modified".
    
    Args:
        callback: CallbackQuery объект
        caption: Новая подпись
        reply_markup: Клавиатура (опционально)
        user_id: ID пользователя для логирования (опционально)
    """
    try:
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=reply_markup
        )
    except TelegramBadRequest as e:
        # Если сообщение не изменилось, это не критическая ошибка
        if "message is not modified" in str(e).lower():
            logger.debug(f"Подпись к фото не изменилась для пользователя {user_id}, пропускаем")
            await callback.answer()
            return True  # Успешно обработано
        # Для других ошибок пробрасываем исключение
        raise
    return False  # Сообщение было отредактировано


async def safe_edit_media(callback: CallbackQuery, media, reply_markup=None, user_id: int = None):
    """
    Безопасно редактирует медиа сообщение, обрабатывая исключение "message is not modified".
    
    Args:
        callback: CallbackQuery объект
        media: Новое медиа (InputMediaPhoto и т.д.)
        reply_markup: Клавиатура (опционально)
        user_id: ID пользователя для логирования (опционально)
    """
    try:
        await callback.message.edit_media(
            media=media,
            reply_markup=reply_markup
        )
    except TelegramBadRequest as e:
        # Если сообщение не изменилось, это не критическая ошибка
        if "message is not modified" in str(e).lower():
            logger.debug(f"Медиа не изменилось для пользователя {user_id}, пропускаем")
            await callback.answer()
            return True  # Успешно обработано
        # Для других ошибок пробрасываем исключение
        raise
    return False  # Сообщение было отредактировано


async def show_next_profile(callback: CallbackQuery, user_id: int):
    """
    Показывает следующую анкету пользователю.
    Используется как внутренняя функция для показа анкет.
    
    Args:
        callback: CallbackQuery объект для ответа
        user_id: ID пользователя в БД (не telegram_id)
    """
    try:
        # Получаем профиль текущего пользователя для получения предпочтений по возрасту
        user_profile = profile_repo.get_by_user_id(user_id)
        if not user_profile:
            await callback.answer("❌ Ваш профиль не найден", show_alert=True)
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
        
        # Если анкет нет
        if not next_profile:
            # Проверяем тип текущего сообщения
            if callback.message.photo:
                # Если сообщение с фото - отправляем новое текстовое
                await callback.message.answer(
                    "😔 Пока нет новых анкет\n\n"
                    "Попробуйте позже или измените настройки поиска.",
                    reply_markup=None
                )
            elif callback.message.text:
                # Если сообщение текстовое - редактируем
                await callback.message.edit_text(
                    "😔 Пока нет новых анкет\n\n"
                    "Попробуйте позже или измените настройки поиска.",
                    reply_markup=None
                )
            else:
                # Если неизвестный тип - отправляем новое
                await callback.message.answer(
                    "😔 Пока нет новых анкет\n\n"
                    "Попробуйте позже или измените настройки поиска.",
                    reply_markup=None
                )
            await callback.answer("Нет новых анкет")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(next_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(next_profile)
        
        # Получаем user_id профиля (не profile.id, а user_id)
        profile_user_id = next_profile.user_id
        
        # Создаем клавиатуру с кнопками
        keyboard = get_profile_keyboard(
            profile_id=next_profile.id,
            user_id=profile_user_id
        )
        
        # Записываем просмотр в ProfileViews
        profile_repo.add_view(viewer_id=user_id, profile_id=next_profile.id)
        logger.debug(f"Просмотр анкеты {next_profile.id} пользователем {user_id} записан")
        
        # Добавляем профиль в историю для кнопки "Назад"
        profile_repo.add_to_history(user_id=user_id, profile_id=next_profile.id)
        logger.debug(f"Анкета {next_profile.id} добавлена в историю для пользователя {user_id}")
        
        # Отправляем или редактируем сообщение с анкетой
        if photo_file_id:
            # Если есть фото - отправляем фото с подписью
            if callback.message.photo:
                # Если сообщение уже содержит фото - редактируем caption и клавиатуру
                try:
                    caption_skipped = await safe_edit_caption(callback, profile_text, keyboard, user_id)
                    if caption_skipped:
                        return
                except Exception:
                    # Если не удалось отредактировать caption (например, фото другое), редактируем медиа
                    try:
                        from aiogram.types import InputMediaPhoto
                        media_skipped = await safe_edit_media(
                            callback,
                            InputMediaPhoto(media=photo_file_id, caption=profile_text),
                            keyboard,
                            user_id
                        )
                        if media_skipped:
                            return
                    except Exception:
                        # Если не удалось отредактировать медиа, отправляем новое сообщение
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=profile_text,
                            reply_markup=keyboard
                        )
            else:
                # Если текущее сообщение текстовое, но новый профиль с фото - редактируем в медиа
                if callback.message.text:
                    try:
                        from aiogram.types import InputMediaPhoto
                        media_skipped = await safe_edit_media(
                            callback,
                            InputMediaPhoto(media=photo_file_id, caption=profile_text),
                            keyboard,
                            user_id
                        )
                        if media_skipped:
                            return
                    except Exception:
                        # Если не удалось отредактировать, отправляем новое сообщение
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=profile_text,
                            reply_markup=keyboard
                        )
                else:
                    # Если нет текста и фото - отправляем новое
                    await callback.message.answer_photo(
                        photo=photo_file_id,
                        caption=profile_text,
                        reply_markup=keyboard
                    )
        else:
            # Если фото нет - отправляем текстовое сообщение
            if callback.message.photo:
                # Если текущее сообщение с фото, а новый профиль без фото - отправляем новое текстовое
                # Нельзя edit_text на сообщении с фото
                await callback.message.answer(
                    text=profile_text,
                    reply_markup=keyboard
                )
            elif callback.message.text:
                # Если текущее сообщение текстовое - редактируем текст
                text_skipped = await safe_edit_text(callback, profile_text, keyboard, user_id)
                if text_skipped:
                    return
            else:
                # Если нет ни текста, ни фото - отправляем новое
                await callback.message.answer(
                    text=profile_text,
                    reply_markup=keyboard
                )
        
        await callback.answer()
        
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
        await callback.answer("❌ Произошла ошибка при загрузке анкеты", show_alert=True)


@router.callback_query(F.data == "show_next_profile")
async def handle_show_next_profile(callback: CallbackQuery):
    """
    Обработчик кнопки "Следующая анкета".
    Показывает следующую анкету пользователю.
    
    Args:
        callback: CallbackQuery объект
    """
    # Получаем пользователя из контекста через репозиторий
    from database.repositories.user_repo import UserRepository
    user_repo = UserRepository()
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        logger.error(f"Пользователь не найден в контексте для callback {callback.data}")
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await callback.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.", show_alert=True)
        return
    
    await show_next_profile(callback, user.id)


@router.callback_query(F.data == "skip_profile")
async def handle_skip_profile(callback: CallbackQuery):
    """
    Обработчик кнопки "👎 Пропустить".
    Пропускает текущую анкету и показывает следующую.
    
    Args:
        callback: CallbackQuery объект
    """
    # Получаем пользователя из контекста через репозиторий
    from database.repositories.user_repo import UserRepository
    user_repo = UserRepository()
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await callback.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.", show_alert=True)
        return
    
    # Просто показываем следующую анкету
    await show_next_profile(callback, user.id)


@router.callback_query(F.data == "back_profile")
async def handle_back_profile(callback: CallbackQuery):
    """
    Обработчик кнопки "↩ Назад".
    Показывает предыдущую анкету из истории просмотров.
    
    Args:
        callback: CallbackQuery объект
    """
    # Получаем пользователя из контекста через репозиторий
    from database.repositories.user_repo import UserRepository
    user_repo = UserRepository()
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
        # Получаем максимальную позицию в истории
        max_position = profile_repo.get_current_position(user.id)
        
        # Если позиция <= 0, значит это первая анкета или истории нет
        if max_position <= 0:
            await callback.answer("Это первая анкета в истории", show_alert=False)
            return
        
        # Получаем все записи истории для пользователя, отсортированные по позиции (от большей к меньшей)
        from database.models.like import ProfileHistory
        from database.models.user import User
        
        # Получаем все записи истории, отсортированные по позиции (от большей к меньшей)
        all_history = list(ProfileHistory.select().where(
            ProfileHistory.user_id == user.id
        ).order_by(ProfileHistory.position.desc()))
        
        if not all_history:
            await callback.answer("В истории нет анкет", show_alert=False)
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
            await callback.answer("В истории нет доступных анкет", show_alert=False)
            return
        
        # Если текущая позиция <= 0, значит это первая анкета
        if current_position <= 0:
            await callback.answer("Это первая анкета в истории", show_alert=False)
            return
        
        # Ищем предыдущий незабаненный профиль
        previous_profile = None
        previous_position = current_position - 1
        
        # Ищем первый незабаненный профиль в истории, начиная с предыдущей позиции
        while previous_position >= 0:
            try:
                history_entry = ProfileHistory.get(
                    (ProfileHistory.user_id == user.id) &
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
            await callback.answer("В истории нет доступных анкет", show_alert=False)
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(previous_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(previous_profile)
        
        # Получаем user_id профиля
        profile_user_id = previous_profile.user_id
        
        # Создаем клавиатуру с кнопками
        keyboard = get_profile_keyboard(
            profile_id=previous_profile.id,
            user_id=profile_user_id
        )
        
        # При следующем "вперед" история продолжится с новой позиции
        
        # Отправляем или редактируем сообщение с анкетой
        if photo_file_id:
            # Если есть фото - отправляем фото с подписью
            if callback.message.photo:
                # Если сообщение уже содержит фото - редактируем caption и клавиатуру
                try:
                    caption_skipped = await safe_edit_caption(callback, profile_text, keyboard, user.id)
                    if caption_skipped:
                        return
                except Exception:
                    # Если не удалось отредактировать caption (например, фото другое), редактируем медиа
                    try:
                        from aiogram.types import InputMediaPhoto
                        media_skipped = await safe_edit_media(
                            callback,
                            InputMediaPhoto(media=photo_file_id, caption=profile_text),
                            keyboard,
                            user.id
                        )
                        if media_skipped:
                            return
                    except Exception:
                        # Если не удалось отредактировать медиа, отправляем новое сообщение
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=profile_text,
                            reply_markup=keyboard
                        )
            else:
                # Если текущее сообщение текстовое, но новый профиль с фото - редактируем в медиа
                if callback.message.text:
                    try:
                        from aiogram.types import InputMediaPhoto
                        media_skipped = await safe_edit_media(
                            callback,
                            InputMediaPhoto(media=photo_file_id, caption=profile_text),
                            keyboard,
                            user.id
                        )
                        if media_skipped:
                            return
                    except Exception:
                        # Если не удалось отредактировать, отправляем новое сообщение
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=profile_text,
                            reply_markup=keyboard
                        )
                else:
                    # Если нет текста и фото - отправляем новое
                    await callback.message.answer_photo(
                        photo=photo_file_id,
                        caption=profile_text,
                        reply_markup=keyboard
                    )
        else:
            # Если фото нет - отправляем текстовое сообщение
            if callback.message.photo:
                # Если текущее сообщение с фото, а новый профиль без фото - отправляем новое текстовое
                await callback.message.answer(
                    text=profile_text,
                    reply_markup=keyboard
                )
            elif callback.message.text:
                # Если текущее сообщение текстовое - редактируем текст
                text_skipped = await safe_edit_text(callback, profile_text, keyboard, user.id)
                if text_skipped:
                    return
            else:
                # Если нет ни текста, ни фото - отправляем новое
                await callback.message.answer(
                    text=profile_text,
                    reply_markup=keyboard
                )
        
        await callback.answer()
        logger.debug(f"Показана предыдущая анкета {previous_profile.id} пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при показе предыдущей анкеты для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при загрузке предыдущей анкеты", show_alert=True)


@router.message(F.text == "💕 Смотреть анкеты")
async def handle_start_browsing(message: Message, user=None):
    """
    Обработчик кнопки "💕 Смотреть анкеты" из главного меню.
    Начинает просмотр анкет, показывая первую анкету.
    
    Args:
        message: Message объект
        user: Пользователь из контекста
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте и БД для команды просмотра анкет")
            return
    
    try:
        # Получаем профиль текущего пользователя для получения предпочтений по возрасту
        user_profile = profile_repo.get_by_user_id(user.id)
        if not user_profile:
            await message.answer("❌ Ваш профиль не найден. Пожалуйста, завершите регистрацию.")
            return
        
        # Получаем предпочтения по возрасту
        min_age = user_profile.min_age_preference
        max_age = user_profile.max_age_preference
        
        # Получаем следующую анкету
        next_profile = matching_service.get_next_profile(
            user_id=user.id,
            min_age=min_age,
            max_age=max_age
        )
        
        # Если анкет нет
        if not next_profile:
            await message.answer(
                "😔 Пока нет новых анкет\n\n"
                "Попробуйте позже или измените настройки поиска.",
                reply_markup=get_next_profile_keyboard()
            )
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(next_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(next_profile)
        
        # Получаем user_id профиля
        profile_user_id = next_profile.user_id
        
        # Создаем клавиатуру
        keyboard = get_profile_keyboard(
            profile_id=next_profile.id,
            user_id=profile_user_id
        )
        
        # Записываем просмотр в ProfileViews
        profile_repo.add_view(viewer_id=user.id, profile_id=next_profile.id)
        logger.debug(f"Просмотр анкеты {next_profile.id} пользователем {user.id} записан")
        
        # Добавляем профиль в историю для кнопки "Назад"
        profile_repo.add_to_history(user_id=user.id, profile_id=next_profile.id)
        logger.debug(f"Анкета {next_profile.id} добавлена в историю для пользователя {user.id}")
        
        # Отправляем анкету
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
        
    except Exception as e:
        logger.error(f"Ошибка при начале просмотра анкет для пользователя {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке анкет. Попробуйте позже.")
