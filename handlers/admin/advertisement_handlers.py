"""
Обработчики управления рекламными кампаниями.
Создание, редактирование, включение/отключение, удаление кампаний и управление медиа.
"""
import logging
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest

from filters.is_admin import IsAdmin
from database.repositories.user_repo import UserRepository
from database.repositories.advertisement_repo import AdvertisementRepository
from keyboards.inline.admin_keyboard import (
    get_admin_main_keyboard,
    get_advertisements_keyboard,
    get_advertisement_actions_keyboard,
    get_advertisement_media_keyboard
)

logger = logging.getLogger(__name__)

# Создание роутера для рекламных кампаний
router = Router()

# Инициализация репозиториев
user_repo = UserRepository()
advertisement_repo = AdvertisementRepository()


class AdvertisementState(StatesGroup):
    """Состояния FSM для управления рекламными кампаниями."""
    waiting_for_text = State()
    """Ожидание текста рекламы (или пропуск, если только медиа)"""
    waiting_for_media = State()
    """Ожидание загрузки медиа (фото/видео)"""
    waiting_for_time = State()
    """Ожидание времени отправки"""
    editing_text = State()
    """Редактирование текста существующей кампании"""
    adding_media = State()
    """Добавление медиа к существующей кампании"""


def format_campaign_info(campaign) -> str:
    """
    Форматирует информацию о рекламной кампании для отображения.
    
    Args:
        campaign: Объект AdvertisementCampaign
        
    Returns:
        Отформатированная строка с информацией о кампании
    """
    status = "✅ Активна" if campaign.is_active else "❌ Неактивна"
    text_preview = campaign.text[:50] + "..." if campaign.text and len(campaign.text) > 50 else (campaign.text or "Нет текста")
    
    # Получаем количество медиа
    media_list = advertisement_repo.get_media_by_campaign(campaign.id)
    media_count = len(media_list)
    
    info = (
        f"📢 Рекламная кампания #{campaign.id}\n\n"
        f"Статус: {status}\n"
        f"Время отправки: {campaign.send_time}\n"
        f"Текст: {text_preview}\n"
        f"Медиа: {media_count} шт.\n"
        f"Создана: {campaign.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    
    if campaign.last_sent_at:
        info += f"Последняя отправка: {campaign.last_sent_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return info


def format_campaigns_list(campaigns) -> str:
    """
    Форматирует список рекламных кампаний для отображения.
    
    Args:
        campaigns: Список объектов AdvertisementCampaign
        
    Returns:
        Отформатированная строка со списком кампаний
    """
    if not campaigns:
        return "📢 Рекламные кампании\n\nПока нет созданных кампаний."
    
    text = "📢 Рекламные кампании\n\n"
    
    for campaign in campaigns:
        status = "✅" if campaign.is_active else "❌"
        text_preview = campaign.text[:30] + "..." if campaign.text and len(campaign.text) > 30 else (campaign.text or "Нет текста")
        
        # Получаем количество медиа
        media_list = advertisement_repo.get_media_by_campaign(campaign.id)
        media_count = len(media_list)
        
        text += (
            f"{status} Кампания #{campaign.id}\n"
            f"   Время: {campaign.send_time} | Медиа: {media_count}\n"
            f"   {text_preview}\n\n"
        )
    
    return text


@router.callback_query(F.data == "admin:advertisements", IsAdmin())
async def admin_advertisements_menu(callback: CallbackQuery):
    """
    Обработчик главного меню рекламы.
    Показывает список всех рекламных кампаний.
    Доступ: все администраторы (временно для тестирования).
    """
    try:
        campaigns = advertisement_repo.get_all()
        campaigns_text = format_campaigns_list(campaigns)
        
        # Создаем клавиатуру со списком кампаний
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        
        # Кнопки для каждой кампании
        for campaign in campaigns:
            status_emoji = "✅" if campaign.is_active else "❌"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} Кампания #{campaign.id} ({campaign.send_time})",
                    callback_data=f"admin:advertisement:actions:{campaign.id}"
                )
            ])
        
        # Кнопка создания новой кампании
        buttons.append([
            InlineKeyboardButton(
                text="➕ Создать рекламу",
                callback_data="admin:advertisement:create"
            )
        ])
        
        # Кнопка "Назад"
        buttons.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin:main"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(
                campaigns_text,
                reply_markup=keyboard
            )
        except TelegramBadRequest:
            # Если сообщение слишком длинное, отправляем новое
            await callback.message.answer(
                campaigns_text,
                reply_markup=keyboard
            )
        
        await callback.answer()
        logger.info(f"Администратор {callback.from_user.id} открыл меню рекламы")
        
    except Exception as e:
        logger.error(f"Ошибка при открытии меню рекламы: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin:advertisement:create", IsAdmin())
async def admin_create_advertisement(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала создания новой рекламной кампании.
    Запрашивает текст рекламы (можно пропустить, если только медиа).
    Доступ: все администраторы.
    """
    await callback.message.answer(
        "📝 Создание новой рекламной кампании\n\n"
        "Шаг 1/3: Введите текст рекламы\n\n"
        "💡 Вы можете пропустить этот шаг, отправив /skip, если хотите использовать только медиа."
    )
    
    await state.set_state(AdvertisementState.waiting_for_text)
    await callback.answer()


@router.message(StateFilter(AdvertisementState.waiting_for_text), IsAdmin())
async def admin_handle_advertisement_text(message: Message, state: FSMContext):
    """
    Обработчик ввода текста рекламы.
    Если текст пропущен (/skip), переходит к добавлению медиа.
    Иначе сохраняет текст и переходит к добавлению медиа.
    """
    user = user_repo.get_by_telegram_id(message.from_user.id)
    
    text = None
    if message.text and message.text.strip() != "/skip":
        text = message.text.strip()
    
    # Сохраняем текст в состоянии
    await state.update_data(text=text)
    
    # Переходим к добавлению медиа
    await message.answer(
        "🖼️ Шаг 2/3: Добавьте медиа (фото или видео)\n\n"
        "Отправьте фото или видео для рекламы.\n"
        "💡 Вы можете пропустить этот шаг, отправив /skip, если хотите использовать только текст.\n"
        "💡 Можно добавить несколько медиа позже в настройках кампании."
    )
    
    await state.set_state(AdvertisementState.waiting_for_media)


@router.message(StateFilter(AdvertisementState.waiting_for_media), IsAdmin(), F.photo)
async def admin_handle_photo(message: Message, state: FSMContext):
    """
    Обработчик загрузки фото для новой рекламной кампании.
    Сохраняет file_id фото и переходит к вводу времени отправки.
    """
    user = user_repo.get_by_telegram_id(message.from_user.id)
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    photo_file_id = photo.file_id
    
    # Сохраняем медиа в состоянии
    data = await state.get_data()
    media_list = data.get("media_list", [])
    media_list.append({
        "file_id": photo_file_id,
        "file_type": "photo"
    })
    await state.update_data(media_list=media_list)
    
    await message.answer(
        f"✅ Фото добавлено ({len(media_list)} шт.)\n\n"
        "💡 Вы можете добавить еще фото/видео или перейти к следующему шагу, отправив /next"
    )


@router.message(StateFilter(AdvertisementState.waiting_for_media), IsAdmin(), F.video)
async def admin_handle_video(message: Message, state: FSMContext):
    """
    Обработчик загрузки видео для новой рекламной кампании.
    Сохраняет file_id видео и переходит к вводу времени отправки.
    """
    user = user_repo.get_by_telegram_id(message.from_user.id)
    
    # Получаем file_id видео
    video_file_id = message.video.file_id
    
    # Сохраняем медиа в состоянии
    data = await state.get_data()
    media_list = data.get("media_list", [])
    media_list.append({
        "file_id": video_file_id,
        "file_type": "video"
    })
    await state.update_data(media_list=media_list)
    
    await message.answer(
        f"✅ Видео добавлено ({len(media_list)} шт.)\n\n"
        "💡 Вы можете добавить еще фото/видео или перейти к следующему шагу, отправив /next"
    )


@router.message(StateFilter(AdvertisementState.waiting_for_media), IsAdmin())
async def admin_handle_media_next(message: Message, state: FSMContext):
    """
    Обработчик перехода к следующему шагу после добавления медиа.
    Проверяет, что есть либо текст, либо медиа, затем запрашивает время отправки.
    """
    data = await state.get_data()
    text = data.get("text")
    media_list = data.get("media_list", [])
    
    # Проверка: должна быть либо текст, либо медиа
    if not text and not media_list:
        await message.answer(
            "❌ Рекламная кампания должна содержать либо текст, либо медиа (или оба).\n\n"
            "Пожалуйста, добавьте текст или медиа."
        )
        return
    
    # Если пользователь отправил /skip или /next, переходим к времени
    if message.text and message.text.strip() in ["/skip", "/next"]:
        await message.answer(
            "⏰ Шаг 3/3: Укажите время отправки\n\n"
            "Введите время в формате ЧЧ:ММ (например, 14:30)\n"
            "Реклама будет отправляться каждый день в указанное время."
        )
        await state.set_state(AdvertisementState.waiting_for_time)
    else:
        await message.answer(
            "💡 Отправьте /next для перехода к следующему шагу или добавьте еще медиа."
        )


@router.message(StateFilter(AdvertisementState.waiting_for_time), IsAdmin())
async def admin_set_advertisement_time(message: Message, state: FSMContext):
    """
    Обработчик установки времени отправки рекламы.
    Создает рекламную кампанию после получения времени.
    """
    user = user_repo.get_by_telegram_id(message.from_user.id)
    
    # Проверяем формат времени (ЧЧ:ММ)
    time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$')
    send_time = message.text.strip()
    
    if not time_pattern.match(send_time):
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например, 14:30)"
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    text = data.get("text")
    media_list = data.get("media_list", [])
    
    # Проверка: должна быть либо текст, либо медиа
    if not text and not media_list:
        await message.answer(
            "❌ Ошибка: Рекламная кампания должна содержать либо текст, либо медиа."
        )
        await state.clear()
        return
    
    try:
        # Создаем рекламную кампанию
        campaign = advertisement_repo.create(
            text=text,
            send_time=send_time,
            created_by_user_id=user.id,
            is_active=True
        )
        
        # Добавляем медиа, если есть
        for idx, media_data in enumerate(media_list):
            advertisement_repo.add_media(
                campaign_id=campaign.id,
                file_id=media_data["file_id"],
                file_type=media_data["file_type"],
                order=idx
            )
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            f"✅ Рекламная кампания #{campaign.id} успешно создана!\n\n"
            f"Время отправки: {send_time}\n"
            f"Текст: {text or 'Нет текста'}\n"
            f"Медиа: {len(media_list)} шт.\n\n"
            "Кампания активна и будет отправляться автоматически."
        )
        
        logger.info(f"Администратор {user.id} создал рекламную кампанию #{campaign.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании рекламной кампании: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при создании рекламной кампании")
        await state.clear()


@router.callback_query(F.data.startswith("admin:advertisement:actions:"), IsAdmin())
async def admin_advertisement_actions(callback: CallbackQuery):
    """
    Обработчик просмотра действий с конкретной рекламной кампанией.
    Показывает информацию о кампании и кнопки действий.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        campaign = advertisement_repo.get_by_id(campaign_id)
        
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        campaign_info = format_campaign_info(campaign)
        keyboard = get_advertisement_actions_keyboard(campaign_id, campaign.is_active)
        
        try:
            await callback.message.edit_text(
                campaign_info,
                reply_markup=keyboard
            )
        except TelegramBadRequest:
            await callback.message.answer(
                campaign_info,
                reply_markup=keyboard
            )
        
        await callback.answer()
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при просмотре действий кампании: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:advertisement:edit_text:"), IsAdmin())
async def admin_edit_advertisement_text(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала редактирования текста рекламной кампании.
    Запрашивает новый текст.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        campaign = advertisement_repo.get_by_id(campaign_id)
        
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        await callback.message.answer(
            f"✏️ Редактирование текста кампании #{campaign_id}\n\n"
            f"Текущий текст: {campaign.text or 'Нет текста'}\n\n"
            "Введите новый текст рекламы:"
        )
        
        await state.set_state(AdvertisementState.editing_text)
        await state.update_data(campaign_id=campaign_id)
        await callback.answer()
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при начале редактирования текста: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(StateFilter(AdvertisementState.editing_text), IsAdmin())
async def admin_save_advertisement_text(message: Message, state: FSMContext):
    """
    Обработчик сохранения нового текста рекламной кампании.
    """
    try:
        data = await state.get_data()
        campaign_id = data.get("campaign_id")
        
        if not campaign_id:
            await message.answer("❌ Ошибка: ID кампании не найден")
            await state.clear()
            return
        
        new_text = message.text.strip() if message.text else None
        
        # Обновляем текст
        success = advertisement_repo.update(campaign_id, text=new_text)
        
        if success:
            campaign = advertisement_repo.get_by_id(campaign_id)
            await message.answer(
                f"✅ Текст кампании #{campaign_id} обновлен!\n\n"
                f"Новый текст: {new_text or 'Нет текста'}"
            )
            logger.info(f"Администратор {message.from_user.id} обновил текст кампании #{campaign_id}")
        else:
            await message.answer("❌ Ошибка при обновлении текста")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении текста: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка")
        await state.clear()


@router.callback_query(F.data.startswith("admin:advertisement:time:"), IsAdmin())
async def admin_set_advertisement_time_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик установки времени отправки рекламной кампании.
    Запрашивает новое время.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        campaign = advertisement_repo.get_by_id(campaign_id)
        
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        await callback.message.answer(
            f"⏰ Изменение времени отправки кампании #{campaign_id}\n\n"
            f"Текущее время: {campaign.send_time}\n\n"
            "Введите новое время в формате ЧЧ:ММ (например, 14:30):"
        )
        
        await state.set_state(AdvertisementState.waiting_for_time)
        await state.update_data(campaign_id=campaign_id, is_editing=True)
        await callback.answer()
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при установке времени: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(StateFilter(AdvertisementState.waiting_for_time), IsAdmin())
async def admin_save_advertisement_time(message: Message, state: FSMContext):
    """
    Обработчик сохранения времени отправки (для редактирования существующей кампании).
    """
    data = await state.get_data()
    is_editing = data.get("is_editing", False)
    
    if is_editing:
        # Редактирование существующей кампании
        campaign_id = data.get("campaign_id")
        
        if not campaign_id:
            await message.answer("❌ Ошибка: ID кампании не найден")
            await state.clear()
            return
        
        # Проверяем формат времени
        time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$')
        send_time = message.text.strip()
        
        if not time_pattern.match(send_time):
            await message.answer(
                "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например, 14:30)"
            )
            return
        
        # Обновляем время
        success = advertisement_repo.update(campaign_id, send_time=send_time)
        
        if success:
            await message.answer(
                f"✅ Время отправки кампании #{campaign_id} обновлено!\n\n"
                f"Новое время: {send_time}"
            )
            logger.info(f"Администратор {message.from_user.id} обновил время кампании #{campaign_id}")
        else:
            await message.answer("❌ Ошибка при обновлении времени")
        
        await state.clear()
    else:
        # Создание новой кампании (уже обработано в admin_set_advertisement_time)
        pass


@router.callback_query(F.data.startswith("admin:advertisement:toggle:"), IsAdmin())
async def admin_toggle_advertisement(callback: CallbackQuery):
    """
    Обработчик включения/выключения рекламной кампании.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        new_status = advertisement_repo.toggle_active(campaign_id)
        
        if new_status is None:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        status_text = "включена" if new_status else "выключена"
        await callback.answer(f"✅ Кампания {status_text}")
        
        # Обновляем сообщение с информацией о кампании
        campaign = advertisement_repo.get_by_id(campaign_id)
        if campaign:
            campaign_info = format_campaign_info(campaign)
            keyboard = get_advertisement_actions_keyboard(campaign_id, campaign.is_active)
            
            try:
                await callback.message.edit_text(
                    campaign_info,
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                pass
        
        logger.info(f"Администратор {callback.from_user.id} {'включил' if new_status else 'выключил'} кампанию #{campaign_id}")
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при переключении статуса кампании: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:advertisement:delete:"), IsAdmin())
async def admin_delete_advertisement(callback: CallbackQuery):
    """
    Обработчик удаления рекламной кампании.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        campaign = advertisement_repo.get_by_id(campaign_id)
        
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        # Удаляем кампанию (медиа удалятся автоматически благодаря каскадному удалению)
        success = advertisement_repo.delete(campaign_id)
        
        if success:
            await callback.answer("✅ Кампания удалена")
            
            # Возвращаемся к списку кампаний
            campaigns = advertisement_repo.get_all()
            campaigns_text = format_campaigns_list(campaigns)
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            buttons = []
            for camp in campaigns:
                status_emoji = "✅" if camp.is_active else "❌"
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} Кампания #{camp.id} ({camp.send_time})",
                        callback_data=f"admin:advertisement:actions:{camp.id}"
                    )
                ])
            
            buttons.append([
                InlineKeyboardButton(
                    text="➕ Создать рекламу",
                    callback_data="admin:advertisement:create"
                )
            ])
            
            buttons.append([
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="admin:main"
                )
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            try:
                await callback.message.edit_text(
                    campaigns_text,
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    campaigns_text,
                    reply_markup=keyboard
                )
            
            logger.info(f"Администратор {callback.from_user.id} удалил кампанию #{campaign_id}")
        else:
            await callback.answer("❌ Ошибка при удалении кампании", show_alert=True)
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при удалении кампании: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:advertisement:media:"), IsAdmin())
async def admin_view_media(callback: CallbackQuery):
    """
    Обработчик просмотра медиа рекламной кампании.
    Показывает список медиа и кнопки управления.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        campaign = advertisement_repo.get_by_id(campaign_id)
        
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        media_list = advertisement_repo.get_media_by_campaign(campaign_id)
        
        if not media_list:
            media_text = f"🖼️ Медиа кампании #{campaign_id}\n\nМедиа пока нет."
        else:
            media_text = f"🖼️ Медиа кампании #{campaign_id}\n\nВсего медиа: {len(media_list)}\n\n"
            for idx, media in enumerate(sorted(media_list, key=lambda x: x.order), 1):
                media_type_emoji = "📷" if media.file_type == "photo" else "🎥"
                media_text += f"{idx}. {media_type_emoji} {media.file_type.upper()} (порядок: {media.order})\n"
        
        keyboard = get_advertisement_media_keyboard(campaign_id, media_list)
        
        try:
            await callback.message.edit_text(
                media_text,
                reply_markup=keyboard
            )
        except TelegramBadRequest:
            await callback.message.answer(
                media_text,
                reply_markup=keyboard
            )
        
        await callback.answer()
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при просмотре медиа: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:advertisement:media_add:"), IsAdmin())
async def admin_add_media(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала добавления медиа к существующей кампании.
    Запрашивает фото или видео.
    Доступ: все администраторы.
    """
    try:
        campaign_id = int(callback.data.split(":")[-1])
        campaign = advertisement_repo.get_by_id(campaign_id)
        
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return
        
        # Получаем текущие медиа для определения следующего order
        media_list = advertisement_repo.get_media_by_campaign(campaign_id)
        next_order = len(media_list)
        
        await callback.message.answer(
            f"➕ Добавление медиа к кампании #{campaign_id}\n\n"
            "Отправьте фото или видео для добавления в кампанию."
        )
        
        await state.set_state(AdvertisementState.adding_media)
        await state.update_data(campaign_id=campaign_id, next_order=next_order)
        await callback.answer()
        
    except ValueError:
        await callback.answer("❌ Неверный ID кампании", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при начале добавления медиа: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(StateFilter(AdvertisementState.adding_media), IsAdmin(), F.photo)
async def admin_handle_add_photo(message: Message, state: FSMContext):
    """
    Обработчик добавления фото к существующей кампании.
    """
    try:
        data = await state.get_data()
        campaign_id = data.get("campaign_id")
        next_order = data.get("next_order", 0)
        
        if not campaign_id:
            await message.answer("❌ Ошибка: ID кампании не найден")
            await state.clear()
            return
        
        # Получаем самое большое фото
        photo = message.photo[-1]
        photo_file_id = photo.file_id
        
        # Добавляем медиа
        media = advertisement_repo.add_media(
            campaign_id=campaign_id,
            file_id=photo_file_id,
            file_type="photo",
            order=next_order
        )
        
        await message.answer(
            f"✅ Фото добавлено в кампанию #{campaign_id}!\n\n"
            f"Порядок: {next_order}\n"
            "💡 Вы можете добавить еще медиа или вернуться к управлению кампанией."
        )
        
        logger.info(f"Администратор {message.from_user.id} добавил фото в кампанию #{campaign_id}")
        
        # Обновляем next_order для следующего медиа
        await state.update_data(next_order=next_order + 1)
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении фото: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при добавлении фото")
        await state.clear()


@router.message(StateFilter(AdvertisementState.adding_media), IsAdmin(), F.video)
async def admin_handle_add_video(message: Message, state: FSMContext):
    """
    Обработчик добавления видео к существующей кампании.
    """
    try:
        data = await state.get_data()
        campaign_id = data.get("campaign_id")
        next_order = data.get("next_order", 0)
        
        if not campaign_id:
            await message.answer("❌ Ошибка: ID кампании не найден")
            await state.clear()
            return
        
        # Получаем file_id видео
        video_file_id = message.video.file_id
        
        # Добавляем медиа
        media = advertisement_repo.add_media(
            campaign_id=campaign_id,
            file_id=video_file_id,
            file_type="video",
            order=next_order
        )
        
        await message.answer(
            f"✅ Видео добавлено в кампанию #{campaign_id}!\n\n"
            f"Порядок: {next_order}\n"
            "💡 Вы можете добавить еще медиа или вернуться к управлению кампанией."
        )
        
        logger.info(f"Администратор {message.from_user.id} добавил видео в кампанию #{campaign_id}")
        
        # Обновляем next_order для следующего медиа
        await state.update_data(next_order=next_order + 1)
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении видео: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при добавлении видео")
        await state.clear()


@router.callback_query(F.data.startswith("admin:advertisement:media_delete:"), IsAdmin())
async def admin_delete_media(callback: CallbackQuery):
    """
    Обработчик удаления медиа из рекламной кампании.
    Доступ: все администраторы.
    """
    try:
        # Формат: admin:advertisement:media_delete:<campaign_id>:<media_id>
        parts = callback.data.split(":")
        campaign_id = int(parts[-2])
        media_id = int(parts[-1])
        
        media = advertisement_repo.get_media_by_id(media_id)
        
        if not media:
            await callback.answer("❌ Медиа не найдено", show_alert=True)
            return
        
        # Удаляем медиа
        success = advertisement_repo.delete_media(media_id)
        
        if success:
            await callback.answer("✅ Медиа удалено")
            
            # Обновляем список медиа
            campaign = advertisement_repo.get_by_id(campaign_id)
            if campaign:
                media_list = advertisement_repo.get_media_by_campaign(campaign_id)
                
                if not media_list:
                    media_text = f"🖼️ Медиа кампании #{campaign_id}\n\nМедиа пока нет."
                else:
                    media_text = f"🖼️ Медиа кампании #{campaign_id}\n\nВсего медиа: {len(media_list)}\n\n"
                    for idx, m in enumerate(sorted(media_list, key=lambda x: x.order), 1):
                        media_type_emoji = "📷" if m.file_type == "photo" else "🎥"
                        media_text += f"{idx}. {media_type_emoji} {m.file_type.upper()} (порядок: {m.order})\n"
                
                keyboard = get_advertisement_media_keyboard(campaign_id, media_list)
                
                try:
                    await callback.message.edit_text(
                        media_text,
                        reply_markup=keyboard
                    )
                except TelegramBadRequest:
                    pass
            
            logger.info(f"Администратор {callback.from_user.id} удалил медиа #{media_id} из кампании #{campaign_id}")
        else:
            await callback.answer("❌ Ошибка при удалении медиа", show_alert=True)
        
    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при удалении медиа: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:advertisement:media_up:"), IsAdmin())
async def admin_reorder_media_up(callback: CallbackQuery):
    """
    Обработчик перемещения медиа вверх (уменьшение порядка).
    Доступ: все администраторы.
    """
    try:
        # Формат: admin:advertisement:media_up:<campaign_id>:<media_id>
        parts = callback.data.split(":")
        campaign_id = int(parts[-2])
        media_id = int(parts[-1])
        
        media = advertisement_repo.get_media_by_id(media_id)
        
        if not media:
            await callback.answer("❌ Медиа не найдено", show_alert=True)
            return
        
        # Получаем все медиа кампании
        media_list = advertisement_repo.get_media_by_campaign(campaign_id)
        sorted_media = sorted(media_list, key=lambda x: x.order)
        
        # Находим текущую позицию
        current_idx = next((idx for idx, m in enumerate(sorted_media) if m.id == media_id), None)
        
        if current_idx is None or current_idx == 0:
            await callback.answer("⚠️ Медиа уже на первом месте", show_alert=True)
            return
        
        # Меняем порядок с предыдущим медиа
        prev_media = sorted_media[current_idx - 1]
        current_order = media.order
        prev_order = prev_media.order
        
        advertisement_repo.reorder_media(media_id, prev_order)
        advertisement_repo.reorder_media(prev_media.id, current_order)
        
        await callback.answer("✅ Порядок изменен")
        
        # Обновляем список медиа
        campaign = advertisement_repo.get_by_id(campaign_id)
        if campaign:
            media_list = advertisement_repo.get_media_by_campaign(campaign_id)
            
            media_text = f"🖼️ Медиа кампании #{campaign_id}\n\nВсего медиа: {len(media_list)}\n\n"
            for idx, m in enumerate(sorted(media_list, key=lambda x: x.order), 1):
                media_type_emoji = "📷" if m.file_type == "photo" else "🎥"
                media_text += f"{idx}. {media_type_emoji} {m.file_type.upper()} (порядок: {m.order})\n"
            
            keyboard = get_advertisement_media_keyboard(campaign_id, media_list)
            
            try:
                await callback.message.edit_text(
                    media_text,
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                pass
        
        logger.info(f"Администратор {callback.from_user.id} переместил медиа #{media_id} вверх в кампании #{campaign_id}")
        
    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при изменении порядка медиа: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:advertisement:media_down:"), IsAdmin())
async def admin_reorder_media_down(callback: CallbackQuery):
    """
    Обработчик перемещения медиа вниз (увеличение порядка).
    Доступ: все администраторы.
    """
    try:
        # Формат: admin:advertisement:media_down:<campaign_id>:<media_id>
        parts = callback.data.split(":")
        campaign_id = int(parts[-2])
        media_id = int(parts[-1])
        
        media = advertisement_repo.get_media_by_id(media_id)
        
        if not media:
            await callback.answer("❌ Медиа не найдено", show_alert=True)
            return
        
        # Получаем все медиа кампании
        media_list = advertisement_repo.get_media_by_campaign(campaign_id)
        sorted_media = sorted(media_list, key=lambda x: x.order)
        
        # Находим текущую позицию
        current_idx = next((idx for idx, m in enumerate(sorted_media) if m.id == media_id), None)
        
        if current_idx is None or current_idx == len(sorted_media) - 1:
            await callback.answer("⚠️ Медиа уже на последнем месте", show_alert=True)
            return
        
        # Меняем порядок со следующим медиа
        next_media = sorted_media[current_idx + 1]
        current_order = media.order
        next_order = next_media.order
        
        advertisement_repo.reorder_media(media_id, next_order)
        advertisement_repo.reorder_media(next_media.id, current_order)
        
        await callback.answer("✅ Порядок изменен")
        
        # Обновляем список медиа
        campaign = advertisement_repo.get_by_id(campaign_id)
        if campaign:
            media_list = advertisement_repo.get_media_by_campaign(campaign_id)
            
            media_text = f"🖼️ Медиа кампании #{campaign_id}\n\nВсего медиа: {len(media_list)}\n\n"
            for idx, m in enumerate(sorted(media_list, key=lambda x: x.order), 1):
                media_type_emoji = "📷" if m.file_type == "photo" else "🎥"
                media_text += f"{idx}. {media_type_emoji} {m.file_type.upper()} (порядок: {m.order})\n"
            
            keyboard = get_advertisement_media_keyboard(campaign_id, media_list)
            
            try:
                await callback.message.edit_text(
                    media_text,
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                pass
        
        logger.info(f"Администратор {callback.from_user.id} переместил медиа #{media_id} вниз в кампании #{campaign_id}")
        
    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при изменении порядка медиа: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
