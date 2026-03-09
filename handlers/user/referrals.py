"""
Обработчики для реферальной системы.
Обработка реферальных ссылок при команде /start и управление рефералами.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from services.referral_service import ReferralService
from utils.referral_links import generate_referral_link
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from loader import get_bot

logger = logging.getLogger(__name__)

# Создание роутера для реферальной системы
router = Router()

# Инициализация репозиториев
user_repo = UserRepository()
profile_repo = ProfileRepository()


async def process_referral_link_async(message: Message, command_args: str, state) -> bool:
    """
    Обрабатывает реферальную ссылку из команды /start.
    
    Парсит реферальный код из аргументов (start=ref_12345) и создает реферальную связь.
    Реферальный код сохраняется в FSM для использования при регистрации.
    
    Эта функция должна быть вызвана из обработчика /start в start.py.
    
    Args:
        message: Сообщение от пользователя
        command_args: Аргументы команды /start
        state: FSM контекст для сохранения данных
        
    Returns:
        bool: True если реферальный код был обработан, False если его не было
    """
    telegram_id = message.from_user.id
    
    # Проверяем наличие аргументов команды
    if not command_args:
        return False
    
    # Получаем или создаем пользователя
    user = user_repo.get_by_telegram_id(telegram_id)
    if not user:
        user = user_repo.create(
            telegram_id=telegram_id,
            username=message.from_user.username
        )
    
    # Инициализируем сервис рефералов
    bot = get_bot()
    referral_service = ReferralService(bot)
    
    # Парсим реферальный код
    referral_code = referral_service.parse_referral_link(command_args)
    
    if referral_code:
        logger.info(f"Обнаружен реферальный код: {referral_code} для пользователя {telegram_id}")
        
        # Обрабатываем реферальную ссылку
        success, error = referral_service.process_referral_on_start(telegram_id, referral_code)
        
        if success:
            # Сохраняем реферальный код в FSM для использования при регистрации
            await state.update_data(referral_code=referral_code)
            logger.info(f"Реферальная ссылка обработана для пользователя {telegram_id}")
            return True
        else:
            logger.warning(f"Ошибка при обработке реферальной ссылки для {telegram_id}: {error}")
            return True  # Код был, но обработка не удалась
    else:
        logger.debug(f"Реферальный код не найден в аргументах: {command_args}")
        return False


@router.message(Command("referral"))
async def cmd_referral(message: Message):
    """
    Обработчик команды /referral.
    Показывает реферальную ссылку пользователя и статистику.
    """
    telegram_id = message.from_user.id
    
    # Получаем пользователя
    user = user_repo.get_by_telegram_id(telegram_id)
    if not user:
        await message.answer(
            "❌ Пользователь не найден. Используйте команду /start для начала работы."
        )
        return
    
    # Проверяем, есть ли у пользователя профиль
    profile = profile_repo.get_by_user_id(user.id)
    if not profile:
        await message.answer(
            "❌ У вас еще нет профиля.\n\n"
            "Сначала пройдите регистрацию, чтобы получить реферальную ссылку."
        )
        return
    
    try:
        # Генерируем реферальную ссылку
        bot = get_bot()
        referral_link = await generate_referral_link(bot, telegram_id)
        
        # Получаем статистику рефералов
        referral_service = ReferralService(bot)
        stats = referral_service.get_referral_stats(user.id)
        
        # Формируем сообщение
        message_text = (
            "🔗 Твоя реферальная ссылка:\n\n"
            f"{referral_link}\n\n"
            "📊 Статистика:\n"
            f"• Приглашено друзей: {stats['total_referrals']}\n"
            f"• Ожидают регистрации: {stats['pending_rewards']}\n\n"
            "💡 Поделись ссылкой с друзьями!\n"
            "🎁 За каждого друга, который зарегистрируется, ты получишь буст своей анкеты!"
        )
        
        await message.answer(message_text)
        logger.info(f"Показана реферальная ссылка для пользователя {telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации реферальной ссылки для {telegram_id}: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при генерации реферальной ссылки. Попробуйте позже."
        )
