"""
Обработчики мэтчей (взаимных симпатий).
Показ списка взаимных симпатий пользователя.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from services.match_service import MatchService
from database.repositories.profile_repo import ProfileRepository
from database.repositories.user_repo import UserRepository
from database.repositories.match_repo import MatchRepository
from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для мэтчей
router = Router()

# Инициализация репозиториев
profile_repo = ProfileRepository()
user_repo = UserRepository()
match_repo = MatchRepository()


def get_match_keyboard(match_id: int, partner_user_id: int, partner_telegram_id: int = None, partner_username: str = None, use_url: bool = True, show_back: bool = False, prev_match_id: int = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для просмотра мэтча.
    
    Args:
        match_id: ID мэтча
        partner_user_id: ID пользователя-партнера по мэтчу (в БД)
        partner_telegram_id: Telegram ID партнера (для ссылки на профиль)
        partner_username: Username партнера (опционально, для ссылки на профиль)
        use_url: Использовать ли url кнопку (True) или callback_data (False)
        show_back: Показывать ли кнопку "Назад"
        prev_match_id: ID предыдущего мэтча (для кнопки "Назад")
    
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    buttons = []
    
    # Кнопка "Написать"
    if use_url:
        # Пытаемся использовать ссылку на профиль
        if partner_username:
            profile_url = f"https://t.me/{partner_username.lstrip('@')}"
        elif partner_telegram_id:
            profile_url = f"tg://user?id={partner_telegram_id}"
        else:
            profile_url = None
        
        if profile_url:
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Написать",
                    url=profile_url
                ),
                InlineKeyboardButton(
                    text="🚨 Жалоба",
                    callback_data=f"complaint:{partner_user_id}"
                )
            ])
        else:
            # Если нет данных для ссылки, используем callback_data
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Написать",
                    callback_data=f"match_message:{partner_user_id}"
                ),
                InlineKeyboardButton(
                    text="🚨 Жалоба",
                    callback_data=f"complaint:{partner_user_id}"
                )
            ])
    else:
        # Используем callback_data версию (fallback при ошибке приватности)
        buttons.append([
            InlineKeyboardButton(
                text="💬 Написать",
                callback_data=f"match_message:{partner_user_id}"
            ),
            InlineKeyboardButton(
                text="🚨 Жалоба",
                callback_data=f"complaint:{partner_user_id}"
            )
        ])
    
    # Кнопки навигации
    nav_buttons = []
    if show_back and prev_match_id:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"prev_match:{prev_match_id}"
            )
        )
    nav_buttons.append(
        InlineKeyboardButton(
            text="➡️ Следующий",
            callback_data=f"next_match:{match_id}"
        )
    )
    buttons.append(nav_buttons)
    
    # Кнопка удаления мэтча
    buttons.append([
        InlineKeyboardButton(
            text="🗑️ Удалить из мэтчей",
            callback_data=f"delete_match:{match_id}"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    return keyboard


async def show_matches_list(message: Message, user_id: int):
    """
    Показывает список мэтчей пользователя.
    
    Args:
        message: Message объект для ответа
        user_id: ID пользователя в БД (не telegram_id)
    """
    try:
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис мэтчей
        match_service = MatchService(bot)
        
        # Получаем список мэтчей пользователя
        matches = match_service.get_user_matches(user_id)
        
        if not matches:
            await message.answer(
                "😔 У вас пока нет взаимных симпатий.\n\n"
                "Продолжайте просматривать анкеты и ставить лайки! 💕"
            )
            return
        
        # Показываем только первый мэтч, остальные можно листать кнопкой "Следующий"
        first_match = matches[0]
        
        # Определяем партнера по мэтчу
        if first_match.user1_id == user_id:
            partner_user_id = first_match.user2_id
        else:
            partner_user_id = first_match.user1_id
        
        # Получаем пользователя-партнера для получения telegram_id и username
        partner_user = user_repo.get_by_id(partner_user_id)
        if not partner_user:
            logger.warning(f"Пользователь-партнер {partner_user_id} не найден для мэтча {first_match.id}")
            await message.answer("❌ Ошибка при загрузке мэтча. Попробуйте позже.")
            return
        
        # Получаем профиль партнера
        partner_profile = profile_repo.get_by_user_id(partner_user_id)
        
        if not partner_profile:
            logger.warning(f"Профиль партнера {partner_user_id} не найден для мэтча {first_match.id}")
            await message.answer("❌ Ошибка при загрузке мэтча. Попробуйте позже.")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(partner_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(partner_profile)
        
        # Добавляем заголовок
        matches_count = len(matches)
        match_text = f"💕 Взаимная симпатия ({matches_count})\n\n{profile_text}"
        
        # Создаем клавиатуру с ссылкой на профиль (без кнопки "Назад" для первого мэтча)
        keyboard = get_match_keyboard(
            match_id=first_match.id,
            partner_user_id=partner_user_id,
            partner_telegram_id=partner_user.telegram_id,
            partner_username=partner_user.username,
            use_url=True,
            show_back=False
        )
        
        # Отправляем анкету мэтча
        try:
            if photo_file_id:
                await message.answer_photo(
                    photo=photo_file_id,
                    caption=match_text,
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    text=match_text,
                    reply_markup=keyboard
                )
        except TelegramBadRequest as e:
            # Если ошибка из-за приватности пользователя, используем callback_data версию
            if "BUTTON_USER_PRIVACY_RESTRICTED" in str(e) or "button_user_privacy" in str(e).lower():
                logger.warning(f"Не удалось создать кнопку со ссылкой на профиль партнера {partner_user_id} из-за настроек приватности, используем callback_data версию")
                # Создаем клавиатуру с callback_data вместо url
                keyboard = get_match_keyboard(
                    match_id=first_match.id,
                    partner_user_id=partner_user_id,
                    partner_telegram_id=partner_user.telegram_id,
                    partner_username=partner_user.username,
                    use_url=False
                )
                # Повторно отправляем с callback_data версией
                if photo_file_id:
                    await message.answer_photo(
                        photo=photo_file_id,
                        caption=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            else:
                # Для других ошибок пробрасываем исключение
                raise
        
        logger.info(f"Показан первый мэтч из {matches_count} для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при показе мэтчей для пользователя {user_id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке мэтчей. Попробуйте позже.")


@router.message(Command("matches"))
@router.message(F.text == "❤️ Мои симпатии")
async def handle_matches(message: Message, user=None):
    """
    Обработчик команды /matches и кнопки "❤️ Мои симпатии".
    Показывает список взаимных симпатий пользователя.
    
    Args:
        message: Message объект
        user: Пользователь из контекста (добавлен UserContextMiddleware)
    """
    # Получаем пользователя из БД, если не пришел из контекста
    if not user:
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            logger.error(f"Пользователь не найден в контексте и БД для команды мэтчей")
            return
    
    await show_matches_list(message, user.id)


@router.callback_query(F.data.startswith("next_match:"))
async def handle_next_match(callback: CallbackQuery):
    """
    Обработчик кнопки "➡️ Следующий" для перехода к следующему мэтчу.
    
    Args:
        callback: CallbackQuery объект
    """
    logger.info(f"Обработка next_match: callback.data={callback.data}, from_user.id={callback.from_user.id}")
    
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
        # Парсим match_id из callback.data
        # Формат: "next_match:{match_id}"
        callback_data = callback.data
        if not callback_data.startswith("next_match:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        try:
            current_match_id = int(callback_data.split(":")[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис мэтчей
        match_service = MatchService(bot)
        
        # Получаем все мэтчи пользователя
        matches = match_service.get_user_matches(user.id)
        
        if not matches:
            await callback.answer("У вас больше нет мэтчей", show_alert=True)
            return
        
        # Находим текущий мэтч и следующий
        current_index = None
        for i, match in enumerate(matches):
            if match.id == current_match_id:
                current_index = i
                break
        
        if current_index is None:
            await callback.answer("Мэтч не найден", show_alert=True)
            return
        
        # Получаем следующий мэтч (с зацикливанием)
        next_index = (current_index + 1) % len(matches)
        next_match = matches[next_index]
        
        # Определяем партнера по мэтчу
        if next_match.user1_id == user.id:
            partner_user_id = next_match.user2_id
        else:
            partner_user_id = next_match.user1_id
        
        # Получаем пользователя-партнера для получения telegram_id и username
        partner_user = user_repo.get_by_id(partner_user_id)
        if not partner_user:
            await callback.answer("Пользователь-партнер не найден", show_alert=True)
            logger.warning(f"Пользователь-партнер {partner_user_id} не найден для мэтча {next_match.id}")
            return
        
        # Получаем профиль партнера
        partner_profile = profile_repo.get_by_user_id(partner_user_id)
        
        if not partner_profile:
            await callback.answer("Профиль партнера не найден", show_alert=True)
            logger.warning(f"Профиль партнера {partner_user_id} не найден для мэтча {next_match.id}")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(partner_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(partner_profile)
        
        # Добавляем заголовок
        matches_count = len(matches)
        match_text = f"💕 Взаимная симпатия ({matches_count})\n\n{profile_text}"
        
        # Определяем, показывать ли кнопку "Назад" (не показываем, если это первый мэтч после зацикливания)
        show_back = next_index != 0
        prev_match_id = current_match_id if show_back else None
        
        # Создаем клавиатуру с ссылкой на профиль
        keyboard = get_match_keyboard(
            match_id=next_match.id,
            partner_user_id=partner_user_id,
            partner_telegram_id=partner_user.telegram_id,
            partner_username=partner_user.username,
            use_url=True,
            show_back=show_back,
            prev_match_id=prev_match_id
        )
        
        # Обновляем сообщение с правильной обработкой фото/текста
        try:
            current_has_photo = callback.message.photo is not None
            new_has_photo = photo_file_id is not None
            
            if new_has_photo:
                # Новое сообщение с фото
                if current_has_photo:
                    # Текущее сообщение тоже с фото - редактируем медиа
                    from aiogram.types import InputMediaPhoto
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=photo_file_id, caption=match_text, parse_mode="HTML"),
                        reply_markup=keyboard
                    )
                else:
                    # Текущее сообщение без фото - удаляем и отправляем новое с фото
                    await callback.message.delete()
                    await callback.message.answer_photo(
                        photo=photo_file_id,
                        caption=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            else:
                # Новое сообщение без фото
                if current_has_photo:
                    # Текущее сообщение с фото - удаляем и отправляем новое текстовое
                    await callback.message.delete()
                    await callback.message.answer(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Текущее сообщение тоже без фото - редактируем текст
                    await callback.message.edit_text(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
        except TelegramBadRequest as e:
            error_message = str(e).lower()
            # Если ошибка "message is not modified" - игнорируем, это не критично
            if "message is not modified" in error_message:
                logger.debug(f"Сообщение не было изменено при переходе к следующему мэтчу для пользователя {user.id}")
                await callback.answer()
                return
            # Если ошибка из-за приватности пользователя, используем callback_data версию
            elif "BUTTON_USER_PRIVACY_RESTRICTED" in str(e) or "button_user_privacy" in error_message:
                logger.warning(f"Не удалось создать кнопку со ссылкой на профиль партнера {partner_user_id} из-за настроек приватности, используем callback_data версию")
                # Создаем клавиатуру с callback_data вместо url
                keyboard = get_match_keyboard(
                    match_id=next_match.id,
                    partner_user_id=partner_user_id,
                    partner_telegram_id=partner_user.telegram_id,
                    partner_username=partner_user.username,
                    use_url=False,
                    show_back=show_back,
                    prev_match_id=prev_match_id
                )
                # Повторно отправляем с callback_data версией
                current_has_photo = callback.message.photo is not None
                new_has_photo = photo_file_id is not None
                
                if new_has_photo:
                    if current_has_photo:
                        from aiogram.types import InputMediaPhoto
                        await callback.message.edit_media(
                            media=InputMediaPhoto(media=photo_file_id, caption=match_text, parse_mode="HTML"),
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.delete()
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                else:
                    if current_has_photo:
                        await callback.message.delete()
                        await callback.message.answer(
                            text=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.edit_text(
                            text=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
            else:
                # Для других ошибок пробрасываем исключение
                raise
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при переходе к следующему мэтчу для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("prev_match:"))
async def handle_prev_match(callback: CallbackQuery):
    """
    Обработчик кнопки "⬅️ Назад" для перехода к предыдущему мэтчу.
    
    Args:
        callback: CallbackQuery объект
    """
    logger.info(f"[handle_prev_match] Начало обработки: callback.data={callback.data}, from_user.id={callback.from_user.id}")
    
    # Всегда отвечаем на callback в начале, чтобы убрать индикатор загрузки
    # (если произойдет ошибка, мы ответим еще раз с сообщением об ошибке)
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback в начале обработки: {e}")
    
    # Получаем пользователя из контекста через репозиторий
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        logger.error(f"Пользователь не найден в контексте для callback {callback.data}")
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        logger.warning(f"Попытка доступа к мэтчам от неверифицированного пользователя {user.id}")
        await callback.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.", show_alert=True)
        return
    
    try:
        # Парсим match_id из callback.data
        # Формат: "prev_match:{match_id}"
        callback_data = callback.data
        if not callback_data.startswith("prev_match:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        try:
            current_match_id = int(callback_data.split(":")[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис мэтчей
        match_service = MatchService(bot)
        
        # Получаем все мэтчи пользователя
        matches = match_service.get_user_matches(user.id)
        
        if not matches:
            await callback.answer("У вас больше нет мэтчей", show_alert=True)
            return
        
        # Находим мэтч, который нужно показать
        # current_match_id из callback_data - это ID мэтча, который нужно показать
        # (это prev_match_id из предыдущего вызова функции get_match_keyboard)
        target_match = None
        target_index = None
        for i, match in enumerate(matches):
            if match.id == current_match_id:
                target_match = match
                target_index = i
                break
        
        if target_match is None:
            logger.warning(f"Мэтч {current_match_id} не найден в списке мэтчей пользователя {user.id}. Доступные мэтчи: {[m.id for m in matches]}")
            await callback.answer("Мэтч не найден", show_alert=True)
            return
        
        logger.debug(f"Найден целевой мэтч {current_match_id} на позиции {target_index} из {len(matches)} мэтчей")
        
        # Используем найденный мэтч (не переходим к предыдущему, т.к. current_match_id уже указывает на нужный мэтч)
        prev_match = target_match
        prev_index = target_index
        
        # Определяем партнера по мэтчу
        if prev_match.user1_id == user.id:
            partner_user_id = prev_match.user2_id
        else:
            partner_user_id = prev_match.user1_id
        
        # Получаем пользователя-партнера для получения telegram_id и username
        partner_user = user_repo.get_by_id(partner_user_id)
        if not partner_user:
            await callback.answer("Пользователь-партнер не найден", show_alert=True)
            logger.warning(f"Пользователь-партнер {partner_user_id} не найден для мэтча {prev_match.id}")
            return
        
        # Получаем профиль партнера
        partner_profile = profile_repo.get_by_user_id(partner_user_id)
        
        if not partner_profile:
            await callback.answer("Профиль партнера не найден", show_alert=True)
            logger.warning(f"Профиль партнера {partner_user_id} не найден для мэтча {prev_match.id}")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(partner_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(partner_profile)
        
        # Добавляем заголовок
        matches_count = len(matches)
        match_text = f"💕 Взаимная симпатия ({matches_count})\n\n{profile_text}"
        
        # Определяем, показывать ли кнопку "Назад" (не показываем, если это первый мэтч после зацикливания)
        show_back = prev_index != 0
        if show_back:
            # Предыдущий мэтч для кнопки "Назад" - это мэтч перед prev_match
            prev_prev_index = (prev_index - 1) % len(matches)
            prev_match_id = matches[prev_prev_index].id
        else:
            prev_match_id = None
        
        # Создаем клавиатуру с ссылкой на профиль
        keyboard = get_match_keyboard(
            match_id=prev_match.id,
            partner_user_id=partner_user_id,
            partner_telegram_id=partner_user.telegram_id,
            partner_username=partner_user.username,
            use_url=True,
            show_back=show_back,
            prev_match_id=prev_match_id
        )
        
        # Обновляем сообщение с правильной обработкой фото/текста
        message_updated = False
        try:
            current_has_photo = callback.message.photo is not None
            new_has_photo = photo_file_id is not None
            
            if new_has_photo:
                # Новое сообщение с фото
                if current_has_photo:
                    # Текущее сообщение тоже с фото - редактируем медиа
                    from aiogram.types import InputMediaPhoto
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=photo_file_id, caption=match_text, parse_mode="HTML"),
                        reply_markup=keyboard
                    )
                    message_updated = True
                else:
                    # Текущее сообщение без фото - удаляем и отправляем новое с фото
                    await callback.message.delete()
                    await callback.message.answer_photo(
                        photo=photo_file_id,
                        caption=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    message_updated = True
            else:
                # Новое сообщение без фото
                if current_has_photo:
                    # Текущее сообщение с фото - удаляем и отправляем новое текстовое
                    await callback.message.delete()
                    await callback.message.answer(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    message_updated = True
                else:
                    # Текущее сообщение тоже без фото - редактируем текст
                    await callback.message.edit_text(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    message_updated = True
        except TelegramBadRequest as e:
            error_message = str(e).lower()
            # Если ошибка "message is not modified" - игнорируем, это не критично
            if "message is not modified" in error_message:
                logger.debug(f"Сообщение не было изменено при переходе к предыдущему мэтчу для пользователя {user.id} (match_id={prev_match.id})")
                message_updated = True  # Считаем, что сообщение уже в правильном состоянии
            # Если ошибка из-за приватности пользователя, используем callback_data версию
            elif "BUTTON_USER_PRIVACY_RESTRICTED" in str(e) or "button_user_privacy" in error_message:
                logger.warning(f"Не удалось создать кнопку со ссылкой на профиль партнера {partner_user_id} из-за настроек приватности, используем callback_data версию")
                # Создаем клавиатуру с callback_data вместо url
                keyboard = get_match_keyboard(
                    match_id=prev_match.id,
                    partner_user_id=partner_user_id,
                    partner_telegram_id=partner_user.telegram_id,
                    partner_username=partner_user.username,
                    use_url=False,
                    show_back=show_back,
                    prev_match_id=prev_match_id
                )
                # Повторно отправляем с callback_data версией
                current_has_photo = callback.message.photo is not None
                new_has_photo = photo_file_id is not None
                
                if new_has_photo:
                    if current_has_photo:
                        from aiogram.types import InputMediaPhoto
                        await callback.message.edit_media(
                            media=InputMediaPhoto(media=photo_file_id, caption=match_text, parse_mode="HTML"),
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.delete()
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                else:
                    if current_has_photo:
                        await callback.message.delete()
                        await callback.message.answer(
                            text=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.edit_text(
                            text=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                message_updated = True
            else:
                # Для других ошибок пробрасываем исключение
                raise
        
        # callback.answer() уже вызван в начале функции
        logger.debug(f"[handle_prev_match] Успешно обработан переход к предыдущему мэтчу для пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при переходе к предыдущему мэтчу для пользователя {user.id}: {e}", exc_info=True)
        # Пытаемся показать сообщение об ошибке (callback.answer() уже был вызван в начале)
        try:
            await callback.answer("❌ Произошла ошибка", show_alert=True)
        except Exception as answer_error:
            logger.warning(f"Не удалось показать сообщение об ошибке: {answer_error}")


@router.callback_query(F.data.startswith("match_message:"))
async def handle_match_message(callback: CallbackQuery):
    """
    Обработчик кнопки "💬 Написать" для мэтча (fallback версия).
    Используется когда ссылка на профиль недоступна из-за настроек приватности.
    Показывает информацию о том, как начать переписку.
    
    Args:
        callback: CallbackQuery объект
    """
    logger.info(f"Обработка match_message: callback.data={callback.data}, from_user.id={callback.from_user.id}")
    
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
        # Парсим partner_user_id из callback.data
        callback_data = callback.data
        if not callback_data.startswith("match_message:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        try:
            partner_user_id = int(callback_data.split(":")[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        # Получаем пользователя-партнера
        partner_user = user_repo.get_by_id(partner_user_id)
        
        if not partner_user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Получаем username партнера или используем ID
        if partner_user.username:
            username_text = f"@{partner_user.username}"
            message_text = (
                f"💬 Для начала переписки\n\n"
                f"Напишите пользователю: {username_text}\n\n"
                f"Или используйте поиск по username в Telegram."
            )
        else:
            username_text = f"ID: {partner_user.telegram_id}"
            message_text = (
                f"💬 Для начала переписки\n\n"
                f"Telegram ID пользователя: {partner_user.telegram_id}\n\n"
                f"Используйте поиск по ID в Telegram или попросите пользователя поделиться username."
            )
        
        await callback.answer(message_text, show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'Написать' для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_match:"))
async def handle_delete_match(callback: CallbackQuery):
    """
    Обработчик кнопки "🗑️ Удалить из мэтчей" для удаления мэтча.
    
    Args:
        callback: CallbackQuery объект
    """
    logger.info(f"[handle_delete_match] Начало обработки: callback.data={callback.data}, from_user.id={callback.from_user.id}")
    
    # Всегда отвечаем на callback в начале, чтобы убрать индикатор загрузки
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback в начале обработки: {e}")
    
    # Получаем пользователя из контекста через репозиторий
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        logger.error(f"Пользователь не найден в контексте для callback {callback.data}")
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        logger.warning(f"Попытка удаления мэтча от неверифицированного пользователя {user.id}")
        await callback.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.", show_alert=True)
        return
    
    try:
        # Парсим match_id из callback.data
        # Формат: "delete_match:{match_id}"
        callback_data = callback.data
        if not callback_data.startswith("delete_match:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        try:
            match_id = int(callback_data.split(":")[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            return
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис мэтчей
        match_service = MatchService(bot)
        
        # Получаем все мэтчи пользователя
        matches = match_service.get_user_matches(user.id)
        
        if not matches:
            await callback.message.delete()
            await callback.message.answer("😔 У вас больше нет мэтчей.")
            return
        
        # Находим мэтч для удаления
        match_to_delete = None
        for match in matches:
            if match.id == match_id:
                match_to_delete = match
                break
        
        if not match_to_delete:
            await callback.answer("Мэтч не найден", show_alert=True)
            logger.warning(f"Мэтч {match_id} не найден для пользователя {user.id}")
            return
        
        # Определяем партнера по мэтчу
        if match_to_delete.user1_id == user.id:
            partner_user_id = match_to_delete.user2_id
        else:
            partner_user_id = match_to_delete.user1_id
        
        # Находим индекс удаляемого мэтча в списке (до удаления)
        deleted_index = None
        for i, match in enumerate(matches):
            if match.id == match_id:
                deleted_index = i
                break
        
        # Удаляем мэтч
        deleted = match_repo.delete(user.id, partner_user_id)
        
        if not deleted:
            logger.warning(f"Не удалось удалить мэтч {match_id} для пользователя {user.id}")
            await callback.answer("❌ Не удалось удалить мэтч", show_alert=True)
            return
        
        logger.info(f"Мэтч {match_id} удален пользователем {user.id}")
        
        # Получаем обновленный список мэтчей
        matches = match_service.get_user_matches(user.id)
        
        if not matches:
            # Если мэтчей больше нет, удаляем сообщение и показываем новое
            try:
                await callback.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")
            
            await callback.message.answer(
                "✅ Мэтч удален.\n\n"
                "😔 У вас больше нет взаимных симпатий.\n\n"
                "Продолжайте просматривать анкеты и ставить лайки! 💕"
            )
            return
        
        # Показываем следующий мэтч после удаления
        # Если удалили последний мэтч, показываем первый
        # Если удалили не последний, показываем мэтч на том же индексе (который был следующим)
        if deleted_index is not None and deleted_index < len(matches):
            next_match = matches[deleted_index]
        else:
            # Если индекс не найден или удалили последний, показываем первый
            next_match = matches[0]
        
        # Определяем партнера по новому мэтчу
        if next_match.user1_id == user.id:
            next_partner_user_id = next_match.user2_id
        else:
            next_partner_user_id = next_match.user1_id
        
        # Получаем пользователя-партнера
        next_partner_user = user_repo.get_by_id(next_partner_user_id)
        if not next_partner_user:
            await callback.answer("Пользователь-партнер не найден", show_alert=True)
            logger.warning(f"Пользователь-партнер {next_partner_user_id} не найден для мэтча {next_match.id}")
            return
        
        # Получаем профиль партнера
        next_partner_profile = profile_repo.get_by_user_id(next_partner_user_id)
        if not next_partner_profile:
            await callback.answer("Профиль партнера не найден", show_alert=True)
            logger.warning(f"Профиль партнера {next_partner_user_id} не найден для мэтча {next_match.id}")
            return
        
        # Получаем фото профиля
        photo_file_id = get_profile_photo_file_id(next_partner_profile)
        
        # Форматируем текст анкеты
        profile_text = format_profile_text(next_partner_profile)
        
        # Добавляем заголовок
        matches_count = len(matches)
        match_text = f"💕 Взаимная симпатия ({matches_count})\n\n{profile_text}"
        
        # Определяем, показывать ли кнопку "Назад"
        next_index = matches.index(next_match) if next_match in matches else 0
        show_back = next_index != 0
        if show_back:
            prev_prev_index = (next_index - 1) % len(matches)
            prev_match_id = matches[prev_prev_index].id
        else:
            prev_match_id = None
        
        # Создаем клавиатуру
        keyboard = get_match_keyboard(
            match_id=next_match.id,
            partner_user_id=next_partner_user_id,
            partner_telegram_id=next_partner_user.telegram_id,
            partner_username=next_partner_user.username,
            use_url=True,
            show_back=show_back,
            prev_match_id=prev_match_id
        )
        
        # Обновляем сообщение
        try:
            current_has_photo = callback.message.photo is not None
            new_has_photo = photo_file_id is not None
            
            if new_has_photo:
                if current_has_photo:
                    from aiogram.types import InputMediaPhoto
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=photo_file_id, caption=match_text, parse_mode="HTML"),
                        reply_markup=keyboard
                    )
                else:
                    await callback.message.delete()
                    await callback.message.answer_photo(
                        photo=photo_file_id,
                        caption=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            else:
                if current_has_photo:
                    await callback.message.delete()
                    await callback.message.answer(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await callback.message.edit_text(
                        text=match_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
        except TelegramBadRequest as e:
            error_message = str(e).lower()
            if "message is not modified" in error_message:
                logger.debug(f"Сообщение не было изменено при удалении мэтча для пользователя {user.id}")
            elif "BUTTON_USER_PRIVACY_RESTRICTED" in str(e) or "button_user_privacy" in error_message:
                logger.warning(f"Не удалось создать кнопку со ссылкой на профиль партнера {next_partner_user_id} из-за настроек приватности, используем callback_data версию")
                keyboard = get_match_keyboard(
                    match_id=next_match.id,
                    partner_user_id=next_partner_user_id,
                    partner_telegram_id=next_partner_user.telegram_id,
                    partner_username=next_partner_user.username,
                    use_url=False,
                    show_back=show_back,
                    prev_match_id=prev_match_id
                )
                # Повторно пытаемся обновить
                current_has_photo = callback.message.photo is not None
                new_has_photo = photo_file_id is not None
                
                if new_has_photo:
                    if current_has_photo:
                        from aiogram.types import InputMediaPhoto
                        await callback.message.edit_media(
                            media=InputMediaPhoto(media=photo_file_id, caption=match_text, parse_mode="HTML"),
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.delete()
                        await callback.message.answer_photo(
                            photo=photo_file_id,
                            caption=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                else:
                    if current_has_photo:
                        await callback.message.delete()
                        await callback.message.answer(
                            text=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.edit_text(
                            text=match_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
            else:
                raise
        
        # Показываем уведомление об успешном удалении
        await callback.answer("✅ Мэтч удален", show_alert=False)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении мэтча для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при удалении мэтча", show_alert=True)

