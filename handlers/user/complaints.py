"""
Обработчики жалоб.
Создание жалоб через FSM, отправка в админ-чат.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.complaint_service import ComplaintService
from states.complaint_state import ComplaintState
from keyboards.inline.complaint_keyboard import (
    get_complaint_reason_keyboard,
    get_complaint_description_keyboard
)
from core.constants import ComplaintReason
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для жалоб
router = Router()


@router.callback_query(F.data.startswith("complaint:"))
async def start_complaint(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "🚨 Жалоба" на анкете.
    Начинает процесс создания жалобы через FSM.
    
    Callback data format: "complaint:{reported_user_id}"
    
    Args:
        callback: CallbackQuery объект
        state: FSM контекст
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
        # Парсим reported_user_id из callback.data
        # Формат: "complaint:{reported_user_id}"
        callback_data = callback.data
        if not callback_data.startswith("complaint:"):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            logger.error(f"Неверный формат callback data: {callback_data}")
            return
        
        try:
            reported_user_id = int(callback_data.split(":")[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            logger.error(f"Не удалось распарсить user_id из callback data: {callback_data}")
            return
        
        # Проверка, что пользователь не жалуется на себя
        if reported_user_id == user.id:
            await callback.answer("❌ Вы не можете пожаловаться на себя", show_alert=True)
            return
        
        # Сохраняем reported_user_id в состоянии
        await state.update_data(reported_user_id=reported_user_id)
        
        # Переходим в состояние выбора причины жалобы
        await state.set_state(ComplaintState.waiting_for_reason)
        
        # Показываем клавиатуру с причинами жалоб
        await callback.message.answer(
            "🚨 <b>Подача жалобы</b>\n\n"
            "Выберите причину жалобы:",
            parse_mode="HTML",
            reply_markup=get_complaint_reason_keyboard()
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при начале создания жалобы для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при создании жалобы", show_alert=True)


@router.callback_query(F.data.startswith("complaint_reason:"), ComplaintState.waiting_for_reason)
async def handle_complaint_reason(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора причины жалобы.
    Сохраняет причину и переходит к вводу описания.
    
    Callback data format: "complaint_reason:{reason}"
    
    Args:
        callback: CallbackQuery объект
        state: FSM контекст
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
    
    try:
        # Парсим reason из callback.data
        # Формат: "complaint_reason:{reason}"
        callback_data = callback.data
        try:
            reason = callback_data.split(":")[1]
        except IndexError:
            await callback.answer("❌ Неверный формат callback", show_alert=True)
            logger.error(f"Не удалось распарсить reason из callback data: {callback_data}")
            return
        
        # Проверка валидности причины
        valid_reasons = [
            ComplaintReason.ADULT_CONTENT,
            ComplaintReason.DRUGS,
            ComplaintReason.FAKE,
            ComplaintReason.HARASSMENT,
            ComplaintReason.OTHER
        ]
        if reason not in valid_reasons:
            await callback.answer("❌ Неверная причина жалобы", show_alert=True)
            logger.error(f"Неверная причина жалобы: {reason}")
            return
        
        # Сохраняем причину в состоянии
        await state.update_data(reason=reason)
        
        # Переходим в состояние ввода описания
        await state.set_state(ComplaintState.waiting_for_description)
        
        # Получаем название причины для отображения
        reason_names = {
            ComplaintReason.ADULT_CONTENT: "18+",
            ComplaintReason.DRUGS: "Наркотики",
            ComplaintReason.FAKE: "Фейк",
            ComplaintReason.HARASSMENT: "Оскорбления",
            ComplaintReason.OTHER: "Другое"
        }
        reason_name = reason_names.get(reason, reason)
        
        # Редактируем сообщение с запросом описания
        await callback.message.edit_text(
            f"🚨 <b>Подача жалобы</b>\n\n"
            f"Причина: <b>{reason_name}</b>\n\n"
            "Введите описание жалобы (опционально):\n"
            "Или нажмите 'Пропустить', чтобы отправить жалобу без описания.",
            parse_mode="HTML",
            reply_markup=get_complaint_description_keyboard()
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе причины жалобы для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "complaint_skip_description", ComplaintState.waiting_for_description)
async def handle_skip_description(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Пропустить" при вводе описания.
    Создает жалобу без описания.
    
    Args:
        callback: CallbackQuery объект
        state: FSM контекст
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
    
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        reported_user_id = data.get("reported_user_id")
        reason = data.get("reason")
        
        if not reported_user_id or not reason:
            await callback.answer("❌ Данные жалобы не найдены", show_alert=True)
            logger.error(f"Данные жалобы не найдены в состоянии для пользователя {user.id}")
            await state.clear()
            return
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис жалоб
        complaint_service = ComplaintService(bot)
        
        # Создаем жалобу без описания
        complaint_id = await complaint_service.create_complaint(
            reporter_id=user.id,
            reported_id=reported_user_id,
            reason=reason,
            description=None
        )
        
        if complaint_id:
            await callback.message.edit_text(
                "✅ <b>Жалоба отправлена</b>\n\n"
                "Спасибо за обращение! Модераторы рассмотрят вашу жалобу.",
                parse_mode="HTML"
            )
            await callback.answer("Жалоба отправлена")
            logger.info(f"Жалоба {complaint_id} создана пользователем {user.id} на {reported_user_id}")
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Не удалось отправить жалобу. Возможно, вы уже жаловались на этого пользователя.",
                parse_mode="HTML"
            )
            await callback.answer("Ошибка при отправке жалобы", show_alert=True)
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при создании жалобы без описания для пользователя {user.id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при создании жалобы", show_alert=True)
        await state.clear()


@router.message(ComplaintState.waiting_for_description)
async def handle_complaint_description(message: Message, state: FSMContext):
    """
    Обработчик ввода описания жалобы.
    Создает жалобу с описанием.
    
    Args:
        message: Message объект с текстом описания
        state: FSM контекст
    """
    # Получаем пользователя из контекста через репозиторий
    from database.repositories.user_repo import UserRepository
    user_repo = UserRepository()
    user = user_repo.get_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Проверка верификации
    if not getattr(user, "is_verified", False):
        await message.answer("❌ Вы не прошли модерацию. Пожалуйста, дождитесь проверки вашей анкеты.")
        return
    
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        reported_user_id = data.get("reported_user_id")
        reason = data.get("reason")
        
        if not reported_user_id or not reason:
            await message.answer("❌ Данные жалобы не найдены. Пожалуйста, начните заново.")
            await state.clear()
            return
        
        # Получаем описание из сообщения
        description = message.text.strip() if message.text else None
        
        # Ограничение длины описания (например, 1000 символов)
        if description and len(description) > 1000:
            await message.answer(
                "❌ Описание слишком длинное. Максимум 1000 символов.\n"
                "Пожалуйста, введите более короткое описание:"
            )
            return
        
        # Получаем экземпляр бота
        bot = get_bot()
        
        # Создаем сервис жалоб
        complaint_service = ComplaintService(bot)
        
        # Создаем жалобу с описанием
        complaint_id = await complaint_service.create_complaint(
            reporter_id=user.id,
            reported_id=reported_user_id,
            reason=reason,
            description=description
        )
        
        if complaint_id:
            await message.answer(
                "✅ <b>Жалоба отправлена</b>\n\n"
                "Спасибо за обращение! Модераторы рассмотрят вашу жалобу.",
                parse_mode="HTML"
            )
            logger.info(f"Жалоба {complaint_id} создана пользователем {user.id} на {reported_user_id} с описанием")
        else:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Не удалось отправить жалобу. Возможно, вы уже жаловались на этого пользователя.",
                parse_mode="HTML"
            )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при создании жалобы с описанием для пользователя {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при создании жалобы. Попробуйте позже.")
        await state.clear()


@router.callback_query(F.data == "complaint_cancel")
async def handle_complaint_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отмены создания жалобы.
    Очищает состояние и отменяет процесс.
    
    Args:
        callback: CallbackQuery объект
        state: FSM контекст
    """
    # Получаем пользователя из контекста через репозиторий (для логирования)
    from database.repositories.user_repo import UserRepository
    user_repo = UserRepository()
    user = user_repo.get_by_telegram_id(callback.from_user.id)
    
    try:
        # Очищаем состояние
        await state.clear()
        
        # Редактируем сообщение
        if callback.message.text or callback.message.caption:
            await callback.message.edit_text("❌ Создание жалобы отменено")
        else:
            await callback.answer("Создание жалобы отменено")
        
        logger.debug(f"Создание жалобы отменено пользователем {user.id if user else 'unknown'}")
        
    except Exception as e:
        logger.error(f"Ошибка при отмене создания жалобы: {e}", exc_info=True)
        await callback.answer("Ошибка при отмене", show_alert=True)
