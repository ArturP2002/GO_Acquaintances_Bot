"""
Сервис для работы с реферальной системой.
Бизнес-логика для обработки реферальных ссылок и выдачи наград.
"""
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

from aiogram import Bot

from database.repositories.referral_repo import ReferralRepository
from database.repositories.user_repo import UserRepository
from database.repositories.settings_repo import SettingsRepository
from services.boost_service import BoostService
from utils.referral_links import parse_referral_code, extract_telegram_id_from_code, generate_referral_code
from core.constants import REFERRAL_BONUS_DEFAULT

logger = logging.getLogger(__name__)


class ReferralService:
    """Сервис для работы с реферальной системой."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис рефералов.
        
        Args:
            bot: Экземпляр бота для отправки уведомлений
        """
        self.bot = bot
        self.referral_repo = ReferralRepository()
        self.user_repo = UserRepository()
        self.settings_repo = SettingsRepository()
    
    def parse_referral_link(self, args: str) -> Optional[str]:
        """
        Парсит реферальный код из аргументов команды /start.
        
        Использует utils/referral_links.py для парсинга.
        
        Args:
            args: Аргументы команды /start (например, "ref_12345" или "start=ref_12345")
            
        Returns:
            str: Реферальный код или None если не найден/невалиден
        """
        return parse_referral_code(args)
    
    def process_referral_on_start(self, invited_telegram_id: int, referral_code: str) -> Tuple[bool, Optional[str]]:
        """
        Обрабатывает реферальную ссылку при команде /start.
        
        Создает реферальную связь, если код валиден и пользователь еще не был приглашен.
        
        Args:
            invited_telegram_id: Telegram ID приглашенного пользователя
            referral_code: Реферальный код (например, "ref_12345")
            
        Returns:
            Tuple[bool, Optional[str]]: (успешно ли обработано, сообщение об ошибке или None)
        """
        try:
            # Извлекаем Telegram ID пригласившего из кода
            inviter_telegram_id = extract_telegram_id_from_code(referral_code)
            if not inviter_telegram_id:
                return False, "Невалидный реферальный код"
            
            # Проверяем, что пользователь не приглашает себя
            if inviter_telegram_id == invited_telegram_id:
                return False, "Нельзя использовать свою реферальную ссылку"
            
            # Получаем пользователей из БД
            inviter = self.user_repo.get_by_telegram_id(inviter_telegram_id)
            invited = self.user_repo.get_by_telegram_id(invited_telegram_id)
            
            if not inviter:
                return False, "Пользователь, который пригласил, не найден"
            
            if not invited:
                # Создаем пользователя, если его еще нет
                invited = self.user_repo.create(
                    telegram_id=invited_telegram_id,
                    username=None
                )
            
            # Проверяем, не был ли уже приглашен этот пользователь
            existing_referral = self.referral_repo.get_by_invited(invited.id)
            if existing_referral:
                logger.info(
                    f"Пользователь {invited_telegram_id} уже был приглашен пользователем {inviter_telegram_id}"
                )
                return True, None  # Уже обработано, но не ошибка
            
            # Создаем реферальную связь
            referral = self.referral_repo.create(
                inviter_id=inviter.id,
                invited_id=invited.id
            )
            
            logger.info(
                f"Создана реферальная связь: inviter_id={inviter.id}, invited_id={invited.id}"
            )
            
            return True, None
            
        except ValueError as e:
            logger.warning(f"Ошибка при обработке реферальной ссылки: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке реферальной ссылки: {e}", exc_info=True)
            return False, "Произошла ошибка при обработке реферальной ссылки"
    
    async def reward_inviter(self, invited_user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Выдает награду пригласившему пользователю после регистрации приглашенного.
        
        Награда: реферальный буст (boost_value из Settings, по умолчанию 10) для пригласившего.
        Награда выдается только один раз за каждого приглашенного.
        
        Args:
            invited_user_id: ID приглашенного пользователя в БД
            
        Returns:
            Tuple[bool, Optional[str]]: (успешно ли выдана награда, сообщение об ошибке или None)
        """
        try:
            # Получаем реферальную связь
            referral = self.referral_repo.get_by_invited(invited_user_id)
            if not referral:
                # Нет реферальной связи - это нормально, пользователь мог зарегистрироваться без реферальной ссылки
                return True, None
            
            # Проверяем, не была ли уже выдана награда
            if referral.reward_given:
                logger.info(f"Награда за реферала уже была выдана для referral_id={referral.id}")
                return True, None
            
            # Получаем настройки для реферального бонуса из БД
            referral_bonus_duration = self.settings_repo.get_int('referral_boost_duration_days', 30)
            
            # Получаем boost_value из БД (по умолчанию 10 для +10 показов)
            referral_bonus_value = self.settings_repo.get_int('referral_bonus', REFERRAL_BONUS_DEFAULT)
            
            # Выдаем реферальный буст пригласившему с boost_value из БД
            # Используем BoostService.add_boost напрямую с нужным boost_value
            from datetime import timedelta
            expires_at = None
            if referral_bonus_duration is not None:
                expires_at = datetime.now() + timedelta(days=referral_bonus_duration)
            
            boost = BoostService.add_boost(
                user_id=referral.inviter_id,
                boost_value=referral_bonus_value,
                expires_at=expires_at
            )
            
            # Отмечаем, что награда выдана
            self.referral_repo.mark_reward_given(referral.id)
            
            logger.info(
                f"Выдана награда за реферала: inviter_id={referral.inviter_id}, "
                f"invited_id={invited_user_id}, boost_id={boost.id}, boost_value={referral_bonus_value}"
            )
            
            # Отправляем уведомление пригласившему (если есть профиль)
            try:
                inviter = self.user_repo.get_by_id(referral.inviter_id)
                if inviter:
                    await self._notify_inviter(inviter.telegram_id)
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пригласившему: {e}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Ошибка при выдаче награды за реферала: {e}", exc_info=True)
            return False, f"Ошибка при выдаче награды: {str(e)}"
    
    async def _notify_inviter(self, inviter_telegram_id: int):
        """
        Отправляет уведомление пригласившему о получении награды.
        
        Args:
            inviter_telegram_id: Telegram ID пригласившего
        """
        try:
            message = (
                "🎉 Поздравляем!\n\n"
                "Твой друг зарегистрировался по твоей реферальной ссылке!\n\n"
                "🎁 Ты получил(а) реферальный буст своей анкеты!\n"
                "Теперь твоя анкета будет показываться чаще другим пользователям."
            )
            await self.bot.send_message(inviter_telegram_id, message)
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление пользователю {inviter_telegram_id}: {e}")
    
    def get_referral_stats(self, user_id: int) -> dict:
        """
        Получает статистику рефералов для пользователя.
        
        Args:
            user_id: ID пользователя в БД
            
        Returns:
            dict: Статистика с ключами:
                - total_referrals: общее количество приглашенных
                - pending_rewards: количество невыданных наград
        """
        total = self.referral_repo.count_by_inviter(user_id)
        pending = len(self.referral_repo.get_pending_rewards(user_id))
        
        return {
            'total_referrals': total,
            'pending_rewards': pending
        }
    
    async def show_random_referral_suggestion(self, user_telegram_id: int) -> bool:
        """
        Показывает случайное предложение пригласить друга с вероятностью 10%.
        
        Используется для случайных напоминаний о реферальной программе во время
        использования бота (например, после просмотра анкет, после лайков и т.д.).
        
        Args:
            user_telegram_id: Telegram ID пользователя
            
        Returns:
            bool: True если предложение было отправлено, False если пропущено (вероятность)
        """
        import random
        from core.constants import REFERRAL_OFFER_PROBABILITY
        from utils.referral_links import generate_referral_link
        
        try:
            # Проверяем вероятность отправки (10% по умолчанию)
            if random.random() > REFERRAL_OFFER_PROBABILITY:
                return False
            
            # Получаем пользователя
            user = self.user_repo.get_by_telegram_id(user_telegram_id)
            if not user:
                return False
            
            # Проверяем, есть ли у пользователя профиль (только для зарегистрированных)
            from database.repositories.profile_repo import ProfileRepository
            profile_repo = ProfileRepository()
            profile = profile_repo.get_by_user_id(user.id)
            if not profile:
                return False
            
            # Генерируем реферальную ссылку
            referral_link = await generate_referral_link(self.bot, user_telegram_id)
            
            # Подсчитываем количество приглашенных пользователей
            referrals_count = self.referral_repo.count_by_inviter(user.id)
            
            # Формируем сообщение
            message = (
                "💡 Хочешь помочь друзьям найти свою половинку?\n\n"
                f"Пригласи друзей по этой ссылке:\n{referral_link}\n\n"
                f"📊 Ты уже пригласил(а): {referrals_count} человек(а)\n\n"
                "🎁 За каждого друга, который зарегистрируется, ты получишь буст своей анкеты (+10 показов)!"
            )
            
            # Отправляем сообщение
            await self.bot.send_message(user_telegram_id, message)
            logger.info(f"Отправлено случайное предложение реферала пользователю {user_telegram_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Не удалось отправить предложение реферала пользователю {user_telegram_id}: {e}")
            return False