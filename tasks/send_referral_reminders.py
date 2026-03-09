"""
Фоновая задача для отправки напоминаний о реферальной программе.
Выполняется каждые 2 часа с вероятностью 10% для случайных пользователей.
"""
import logging
import random
from datetime import datetime, timedelta

from loader import get_bot
from database.models.user import User
from database.models.profile import Profile
from database.models.referral import Referral
from core.constants import REFERRAL_OFFER_PROBABILITY, ACTIVE_USER_THRESHOLD_DAYS

logger = logging.getLogger(__name__)


def generate_referral_link(bot_username: str, user_telegram_id: int) -> str:
    """
    Генерирует реферальную ссылку для пользователя.
    
    Args:
        bot_username: Username бота в Telegram
        user_telegram_id: Telegram ID пользователя
        
    Returns:
        str: Реферальная ссылка
    """
    # Генерируем код на основе telegram_id (можно использовать хеш для безопасности)
    referral_code = f"ref_{user_telegram_id}"
    return f"https://t.me/{bot_username}?start={referral_code}"


async def send_referral_reminders_task():
    """
    Фоновая задача для отправки напоминаний о реферальной программе.
    Выполняется каждые 2 часа.
    
    Логика:
    1. Выбирает активных пользователей (last_active < 3 дня назад)
    2. С вероятностью 10% отправляет напоминание о реферальной программе
    3. Отправляет реферальную ссылку пользователя
    """
    try:
        logger.info("Запуск задачи отправки напоминаний о рефералах...")
        
        bot = get_bot()
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        
        if not bot_username:
            logger.error("Не удалось получить username бота")
            return
        
        # Получаем активных пользователей (заходили менее 3 дней назад)
        active_threshold = datetime.now() - timedelta(days=ACTIVE_USER_THRESHOLD_DAYS)
        
        active_users = list(
            User.select()
            .where(
                (User.is_banned == False) &
                (User.is_verified == True) &
                (User.is_active == True) &
                (
                    (User.last_active.is_null()) |
                    (User.last_active >= active_threshold)
                )
            )
        )
        
        logger.info(f"Найдено активных пользователей: {len(active_users)}")
        
        sent_count = 0
        skipped_count = 0
        
        for user in active_users:
            try:
                # Проверяем вероятность отправки (10%)
                if random.random() > REFERRAL_OFFER_PROBABILITY:
                    skipped_count += 1
                    continue
                
                # Проверяем, есть ли у пользователя профиль
                try:
                    profile = Profile.get(Profile.user_id == user.id)
                except Profile.DoesNotExist:
                    # У пользователя нет профиля, пропускаем
                    skipped_count += 1
                    continue
                
                # Проверяем, не отправляли ли мы уже напоминание недавно
                # (можно добавить поле last_referral_reminder в User для отслеживания)
                
                # Генерируем реферальную ссылку
                referral_link = generate_referral_link(bot_username, user.telegram_id)
                
                # Подсчитываем количество приглашенных пользователей
                referrals_count = Referral.select().where(
                    Referral.inviter_id == user.id
                ).count()
                
                # Формируем сообщение
                message = (
                    "👋 Привет!\n\n"
                    "💡 Хочешь помочь друзьям найти свою половинку?\n\n"
                    f"Пригласи друзей по этой ссылке:\n{referral_link}\n\n"
                    f"📊 Ты уже пригласил(а): {referrals_count} человек(а)\n\n"
                    "🎁 За каждого друга, который зарегистрируется, ты получишь буст своей анкеты!"
                )
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    disable_notification=False
                )
                
                sent_count += 1
                logger.debug(f"Отправлено напоминание пользователю {user.telegram_id}")
                
            except Exception as e:
                logger.warning(
                    f"Ошибка при отправке напоминания пользователю {user.telegram_id}: {e}"
                )
                # Продолжаем обработку других пользователей
                continue
        
        logger.info(
            f"Задача отправки напоминаний завершена. "
            f"Отправлено: {sent_count}, пропущено: {skipped_count}"
        )
        
    except Exception as e:
        logger.error(
            f"Ошибка при выполнении задачи отправки напоминаний о рефералах: {e}",
            exc_info=True
        )
