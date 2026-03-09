"""
Обработчик регистрации пользователей.
Пошаговый сбор данных анкеты через FSM.
"""
import logging
import random
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import default_state

from states.registration_state import RegistrationState
from services.profile_service import ProfileService
from services.referral_service import ReferralService
from services.moderation_service import ModerationService
from database.repositories.user_repo import UserRepository
from database.repositories.settings_repo import SettingsRepository
from core.constants import VIDEO_NOTE_TASKS, MIN_AGE_DEFAULT
from config import config
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для регистрации
router = Router()

# Инициализация сервисов
profile_service = ProfileService()
user_repo = UserRepository()


def get_gender_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру для выбора пола."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")],
            [KeyboardButton(text="Другой")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


@router.message(Command("register"), StateFilter(default_state))
@router.message(F.text == "Регистрация", StateFilter(default_state))
async def start_registration(message: Message, state: FSMContext):
    """
    Начинает процесс регистрации.
    Проверяет, не зарегистрирован ли пользователь уже.
    Защита от мультиаккаунтов: один telegram_id = одна регистрация.
    """
    telegram_id = message.from_user.id
    user = user_repo.get_by_telegram_id(telegram_id)
    
    # Защита от мультиаккаунтов: проверка существования пользователя
    if user:
        # Проверка, есть ли уже профиль
        from database.repositories.profile_repo import ProfileRepository
        profile_repo = ProfileRepository()
        existing_profile = profile_repo.get_by_user_id(user.id)
        if existing_profile:
            logger.info(f"Попытка повторной регистрации: пользователь {telegram_id} уже зарегистрирован")
            await message.answer(
                "✅ Вы уже зарегистрированы!\n\n"
                "Используйте команды бота для просмотра анкет и взаимодействия."
            )
            return
        
        # Если пользователь существует, но профиля нет - возможно незавершенная регистрация
        # Разрешаем продолжить регистрацию
        logger.debug(f"Пользователь {telegram_id} существует, но профиля нет - продолжаем регистрацию")
    
    # Проверка на бан
    if user and user.is_banned:
        logger.warning(f"Попытка регистрации забаненным пользователем: {telegram_id}")
        await message.answer(
            "❌ Ваш аккаунт заблокирован.\n\n"
            "Регистрация недоступна."
        )
        return
    
    # Начало регистрации
    await message.answer(
        "👋 Добро пожаловать в регистрацию!\n\n"
        "Мы поможем вам создать анкету. Давайте начнем!\n\n"
        "📝 Шаг 1/7: Как тебя зовут?\n"
        "Напиши свое имя:"
    )
    await state.set_state(RegistrationState.waiting_for_name)


@router.message(StateFilter(RegistrationState.waiting_for_name))
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает ввод имени."""
    name = message.text.strip()
    
    # Валидация имени
    if not name or len(name) < 2:
        await message.answer(
            "❌ Имя слишком короткое. Пожалуйста, введи имя (минимум 2 символа):"
        )
        return
    
    if len(name) > 50:
        await message.answer(
            "❌ Имя слишком длинное. Пожалуйста, введи имя (максимум 50 символов):"
        )
        return
    
    # Сохранение имени
    await state.update_data(name=name)
    
    await message.answer(
        f"✅ Отлично, {name}!\n\n"
        "📝 Шаг 2/7: Сколько тебе лет?\n"
        "Напиши свой возраст (только число):"
    )
    await state.set_state(RegistrationState.waiting_for_age)


@router.message(StateFilter(RegistrationState.waiting_for_age))
async def process_age(message: Message, state: FSMContext):
    """Обрабатывает ввод возраста с проверкой на бан."""
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введи возраст числом (например, 25):"
        )
        return
    
    # Валидация возраста
    if age < 1 or age > 120:
        await message.answer(
            "❌ Возраст должен быть от 1 до 120 лет. Пожалуйста, введи корректный возраст:"
        )
        return
    
    # Получаем минимальный возраст из БД
    min_age = SettingsRepository.get_int("min_age", MIN_AGE_DEFAULT)
    
    # Проверка минимального возраста и бан при необходимости
    if age < min_age:
        # Бан пользователя
        user = user_repo.get_by_telegram_id(message.from_user.id)
        if user:
            user_repo.ban_user(user.id)
        else:
            # Создаем пользователя и сразу баним
            user = user_repo.create(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                is_banned=True
            )
        
        await message.answer(
            f"❌ К сожалению, регистрация доступна только для пользователей старше {min_age} лет.\n\n"
            "Ваш аккаунт был заблокирован."
        )
        await state.clear()
        return
    
    # Сохранение возраста
    await state.update_data(age=age)
    
    await message.answer(
        f"✅ Возраст {age} лет сохранен!\n\n"
        "📝 Шаг 3/7: Какой у тебя пол?\n"
        "Выбери из предложенных вариантов:",
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(RegistrationState.waiting_for_gender)


@router.message(StateFilter(RegistrationState.waiting_for_gender))
async def process_gender(message: Message, state: FSMContext):
    """Обрабатывает выбор пола."""
    gender_text = message.text.strip()
    
    # Валидация пола
    valid_genders = ["Мужской", "Женский", "Другой"]
    if gender_text not in valid_genders:
        await message.answer(
            "❌ Пожалуйста, выбери пол из предложенных вариантов:",
            reply_markup=get_gender_keyboard()
        )
        return
    
    # Сохранение пола
    await state.update_data(gender=gender_text)
    
    await message.answer(
        f"✅ Пол сохранен!\n\n"
        "📝 Шаг 4/7: В каком городе ты живешь?\n"
        "Напиши название города (или пропусти, нажав /skip):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationState.waiting_for_city)


@router.message(StateFilter(RegistrationState.waiting_for_city))
async def process_city(message: Message, state: FSMContext):
    """Обрабатывает ввод города."""
    city = message.text.strip()
    
    # Пропуск города
    if city.lower() in ["/skip", "пропустить", "skip"]:
        city = None
    else:
        # Валидация города
        if len(city) > 100:
            await message.answer(
                "❌ Название города слишком длинное. Пожалуйста, введи корректное название (максимум 100 символов):"
            )
            return
    
    # Сохранение города
    await state.update_data(city=city)
    
    city_text = f" в городе {city}" if city else ""
    await message.answer(
        f"✅ Город{city_text} сохранен!\n\n"
        "📝 Шаг 5/7: Расскажи о себе\n"
        "Напиши краткое описание (био) или пропусти, нажав /skip:"
    )
    await state.set_state(RegistrationState.waiting_for_bio)


@router.message(StateFilter(RegistrationState.waiting_for_bio))
async def process_bio(message: Message, state: FSMContext):
    """Обрабатывает ввод описания (био)."""
    bio = message.text.strip()
    
    # Пропуск био
    if bio.lower() in ["/skip", "пропустить", "skip"]:
        bio = None
    else:
        # Валидация био
        if len(bio) > 1000:
            await message.answer(
                "❌ Описание слишком длинное. Пожалуйста, сократи до 1000 символов:"
            )
            return
    
    # Сохранение био
    await state.update_data(bio=bio)
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "📝 Шаг 6/7: Загрузи свое фото\n"
        "Отправь фото для своей анкеты:"
    )
    await state.set_state(RegistrationState.waiting_for_photo)


@router.message(StateFilter(RegistrationState.waiting_for_photo), F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Обрабатывает загрузку фото."""
    # Получение file_id самого большого фото
    photo = message.photo[-1]
    photo_file_id = photo.file_id
    
    # Генерация случайного задания для кружка
    task = random.choice(VIDEO_NOTE_TASKS)
    
    # Сохранение file_id фото и задания
    await state.update_data(photo_file_id=photo_file_id, video_note_task=task)
    
    await message.answer(
        "✅ Фото загружено!\n\n"
        f"📝 Шаг 7/7: Запиши кружок (video note)\n\n"
        f"🎯 Задание: {task}\n\n"
        "Это необходимо для модерации. Запиши короткое видео-сообщение (кружок) с выполнением задания:"
    )
    await state.set_state(RegistrationState.waiting_for_video_note)


@router.message(StateFilter(RegistrationState.waiting_for_photo))
async def process_photo_invalid(message: Message, state: FSMContext):
    """Обрабатывает некорректный ввод на этапе загрузки фото."""
    await message.answer(
        "❌ Пожалуйста, отправь фото. Используй кнопку 📷 для отправки фото:"
    )


@router.message(StateFilter(RegistrationState.waiting_for_video_note), F.video_note)
async def process_video_note(message: Message, state: FSMContext):
    """Обрабатывает загрузку кружка и завершает регистрацию или обновляет существующий профиль."""
    video_note = message.video_note
    video_note_file_id = video_note.file_id
    
    # Получение всех данных из состояния
    data = await state.get_data()
    
    # Получение задания для кружка из состояния
    video_note_task = data.get('video_note_task')
    
    # Проверяем, есть ли уже профиль у пользователя (повторная отправка после отклонения)
    user = user_repo.get_by_telegram_id(message.from_user.id)
    existing_profile = None
    if user:
        from database.repositories.profile_repo import ProfileRepository
        profile_repo = ProfileRepository()
        existing_profile = profile_repo.get_by_user_id(user.id)
    
    if existing_profile:
        # Обновление существующего профиля (повторная отправка кружка после отклонения)
        logger.info(f"Обновление кружка для существующего профиля {existing_profile.id} пользователя {message.from_user.id}")
        
        # Обновляем или создаем медиа с новым кружком
        from database.repositories.profile_repo import ProfileRepository
        profile_repo = ProfileRepository()
        
        # Удаляем старый кружок, если есть
        old_video_note = profile_repo.get_video_note(existing_profile.id)
        if old_video_note:
            old_video_note.delete_instance()
        
        # Добавляем новый кружок
        profile_repo.add_media(
            profile_id=existing_profile.id,
            video_note_file_id=video_note_file_id
        )
        
        # Генерируем новое задание, если его нет в состоянии
        if not video_note_task:
            video_note_task = random.choice(VIDEO_NOTE_TASKS)
        
        # Создаем новую задачу модерации
        try:
            bot = get_bot()
            moderation_service = ModerationService(bot)
            moderation_id = await moderation_service.create_moderation_task(
                user_id=user.id,
                profile_id=existing_profile.id,
                task=video_note_task
            )
            if moderation_id:
                logger.info(f"Задача модерации {moderation_id} создана для обновленного профиля пользователя {message.from_user.id}")
            else:
                logger.error(f"Не удалось создать задачу модерации для обновленного профиля пользователя {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке обновленного профиля в группу модерации: {e}", exc_info=True)
        
        await message.answer(
            "✅ Кружок обновлен!\n\n"
            "Твоя анкета отправлена на повторную модерацию.\n"
            "Ожидай уведомления о результате модерации."
        )
        logger.info(f"Кружок обновлен для профиля {existing_profile.id} пользователя {message.from_user.id}")
    else:
        # Создание нового профиля
        result = profile_service.create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            name=data.get('name'),
            age=data.get('age'),
            gender=data.get('gender'),
            city=data.get('city'),
            bio=data.get('bio'),
            photo_file_id=data.get('photo_file_id'),
            video_note_file_id=video_note_file_id,
            video_note_task=video_note_task
        )
        
        if result['success']:
            user = result.get('user')
            profile = result.get('profile')
            
            # Отправка в группу модерации, если есть кружок
            if video_note_file_id and video_note_task and user and profile:
                try:
                    bot = get_bot()
                    moderation_service = ModerationService(bot)
                    moderation_id = await moderation_service.create_moderation_task(
                        user_id=user.id,
                        profile_id=profile.id,
                        task=video_note_task
                    )
                    if moderation_id:
                        logger.info(f"Задача модерации {moderation_id} создана и отправлена для пользователя {message.from_user.id}")
                    else:
                        logger.error(f"Не удалось создать задачу модерации для пользователя {message.from_user.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке в группу модерации: {e}", exc_info=True)
            
            # Проверяем реферальный код и выдаем награду пригласившему
            referral_code = data.get('referral_code')
            if referral_code:
                try:
                    bot = get_bot()
                    referral_service = ReferralService(bot)
                    if user:
                        success, error = await referral_service.reward_inviter(user.id)
                        if success:
                            logger.info(f"Награда за реферала выдана для пользователя {message.from_user.id}")
                        else:
                            logger.warning(f"Не удалось выдать награду за реферала: {error}")
                except Exception as e:
                    logger.error(f"Ошибка при выдаче награды за реферала: {e}", exc_info=True)
            
            await message.answer(
                "🎉 Поздравляем! Регистрация завершена!\n\n"
                "✅ Твоя анкета создана и отправлена на модерацию.\n"
                "После проверки модераторами ты сможешь начать искать знакомства!\n\n"
                "Ожидай уведомления о результате модерации."
            )
            logger.info(f"Профиль создан для пользователя {message.from_user.id}")
        else:
            error_msg = result.get('error', 'Неизвестная ошибка')
            await message.answer(
                f"❌ Произошла ошибка при создании профиля: {error_msg}\n\n"
                "Пожалуйста, попробуй зарегистрироваться снова, используя команду /register"
            )
            logger.error(f"Ошибка создания профиля для {message.from_user.id}: {error_msg}")
    
    # Очистка состояния
    await state.clear()


@router.message(StateFilter(RegistrationState.waiting_for_video_note))
async def process_video_note_invalid(message: Message, state: FSMContext):
    """Обрабатывает некорректный ввод на этапе загрузки кружка."""
    await message.answer(
        "❌ Пожалуйста, отправь кружок (video note). Используй кнопку 📹 для записи видео-сообщения:"
    )


@router.message(F.video_note)
async def process_video_note_reupload(message: Message, state: FSMContext):
    """
    Обрабатывает повторную отправку кружка после отклонения профиля.
    Работает вне состояния регистрации для пользователей с существующим, но не верифицированным профилем.
    """
    # Проверяем, не находимся ли мы в процессе регистрации
    current_state = await state.get_state()
    if current_state == RegistrationState.waiting_for_video_note:
        # Если мы в состоянии регистрации, пропускаем - обработчик выше обработает
        return
    
    # Проверяем, есть ли у пользователя существующий, но не верифицированный профиль
    user = user_repo.get_by_telegram_id(message.from_user.id)
    if not user or user.is_verified:
        # Если пользователь верифицирован или не существует, пропускаем
        return
    
    # Проверяем наличие профиля
    from database.repositories.profile_repo import ProfileRepository
    profile_repo = ProfileRepository()
    existing_profile = profile_repo.get_by_user_id(user.id)
    
    if not existing_profile:
        # Если профиля нет, пропускаем - это не повторная отправка
        return
    
    # Это повторная отправка кружка после отклонения
    video_note = message.video_note
    video_note_file_id = video_note.file_id
    
    logger.info(f"Повторная отправка кружка для профиля {existing_profile.id} пользователя {message.from_user.id}")
    
    # Удаляем старый кружок, если есть
    old_video_note = profile_repo.get_video_note(existing_profile.id)
    if old_video_note:
        old_video_note.delete_instance()
    
    # Добавляем новый кружок
    profile_repo.add_media(
        profile_id=existing_profile.id,
        video_note_file_id=video_note_file_id
    )
    
    # Генерируем новое задание
    video_note_task = random.choice(VIDEO_NOTE_TASKS)
    
    # Создаем новую задачу модерации
    try:
        bot = get_bot()
        moderation_service = ModerationService(bot)
        moderation_id = await moderation_service.create_moderation_task(
            user_id=user.id,
            profile_id=existing_profile.id,
            task=video_note_task
        )
        if moderation_id:
            logger.info(f"Задача модерации {moderation_id} создана для повторно отправленного профиля пользователя {message.from_user.id}")
            await message.answer(
                "✅ Кружок обновлен!\n\n"
                "Твоя анкета отправлена на повторную модерацию.\n"
                "Ожидай уведомления о результате модерации."
            )
        else:
            logger.error(f"Не удалось создать задачу модерации для повторно отправленного профиля пользователя {message.from_user.id}")
            await message.answer(
                "❌ Произошла ошибка при отправке анкеты на модерацию.\n"
                "Пожалуйста, попробуй еще раз."
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке обновленного профиля в группу модерации: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при отправке анкеты на модерацию.\n"
            "Пожалуйста, попробуй еще раз."
        )


@router.message(StateFilter(RegistrationState))
async def process_unknown_state(message: Message, state: FSMContext):
    """Обрабатывает сообщения в неизвестном состоянии регистрации."""
    current_state = await state.get_state()
    logger.warning(f"Неизвестное состояние регистрации: {current_state} для пользователя {message.from_user.id}")
    await message.answer(
        "❌ Произошла ошибка в процессе регистрации.\n\n"
        "Пожалуйста, начни регистрацию заново, используя команду /register"
    )
    await state.clear()
