"""
Сервис для работы с жалобами.
Создание жалоб, отправка в админ-чат, обработка действий модераторов.
"""
import logging
from typing import Optional

from aiogram import Bot

from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.complaint_repo import ComplaintRepository
from core.constants import ComplaintStatus, ComplaintReason
from config import config
from keyboards.inline.complaint_keyboard import get_admin_complaint_keyboard

# Настройка логирования
logger = logging.getLogger(__name__)


class ComplaintService:
    """Сервис для работы с жалобами."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис жалоб.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
        """
        self.bot = bot
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.complaint_repo = ComplaintRepository()
        # Используем ADMIN_GROUP_ID если есть, иначе MODERATION_GROUP_ID
        self.admin_group_id = config.ADMIN_GROUP_ID or config.MODERATION_GROUP_ID
    
    async def create_complaint(self, reporter_id: int, reported_id: int, 
                               reason: str, description: Optional[str] = None) -> Optional[int]:
        """
        Создает жалобу и отправляет её в админ-чат.
        
        Args:
            reporter_id: ID пользователя, который подал жалобу
            reported_id: ID пользователя, на которого пожаловались
            reason: Причина жалобы (из ComplaintReason)
            description: Описание жалобы (опционально)
            
        Returns:
            ID созданной жалобы или None в случае ошибки
        """
        try:
            # Проверка, не существует ли уже жалоба от этого пользователя на этого пользователя
            if self.complaint_repo.exists(reporter_id, reported_id):
                logger.warning(f"Жалоба от {reporter_id} на {reported_id} уже существует")
                return None
            
            # Создание жалобы
            complaint = self.complaint_repo.create(
                reporter_id=reporter_id,
                reported_id=reported_id,
                reason=reason,
                description=description
            )
            
            # Отправка в админ-чат
            await self.notify_admin(complaint.id)
            
            logger.info(f"Жалоба {complaint.id} создана и отправлена в админ-чат")
            return complaint.id
            
        except Exception as e:
            logger.error(f"Ошибка при создании жалобы: {e}", exc_info=True)
            return None
    
    async def notify_admin(self, complaint_id: int) -> bool:
        """
        Отправляет жалобу в админ-чат с информацией о пользователях.
        
        Args:
            complaint_id: ID жалобы
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        try:
            # Получение жалобы
            complaint = self.complaint_repo.get_by_id(complaint_id)
            if not complaint:
                logger.error(f"Жалоба {complaint_id} не найдена")
                return False
            
            # Получение пользователей
            reporter = self.user_repo.get_by_id(complaint.reporter_id)
            reported = self.user_repo.get_by_id(complaint.reported_id)
            
            if not reporter or not reported:
                logger.error(f"Пользователи для жалобы {complaint_id} не найдены")
                return False
            
            # Получение профиля пользователя, на которого пожаловались
            reported_profile = self.profile_repo.get_by_user_id(complaint.reported_id)
            
            # Формирование текста сообщения
            message_text = self._format_complaint_message(
                complaint=complaint,
                reporter=reporter,
                reported=reported,
                reported_profile=reported_profile
            )
            
            # Получение фото профиля (если есть)
            photo_file_id = None
            if reported_profile:
                main_photo = self.profile_repo.get_main_photo(reported_profile.id)
                if main_photo and main_photo.photo_file_id:
                    photo_file_id = main_photo.photo_file_id
            
            # Отправка сообщения в админ-чат
            if photo_file_id:
                # Отправляем фото с текстом
                await self.bot.send_photo(
                    chat_id=self.admin_group_id,
                    photo=photo_file_id,
                    caption=message_text,
                    parse_mode="HTML",
                    reply_markup=get_admin_complaint_keyboard(complaint_id)
                )
            else:
                # Отправляем только текст
                await self.bot.send_message(
                    chat_id=self.admin_group_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=get_admin_complaint_keyboard(complaint_id)
                )
            
            logger.info(f"Жалоба {complaint_id} отправлена в админ-чат")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке жалобы в админ-чат: {e}", exc_info=True)
            return False
    
    def _format_complaint_message(self, complaint, reporter, reported, 
                                  reported_profile) -> str:
        """
        Формирует текст сообщения для жалобы.
        
        Args:
            complaint: Объект Complaint
            reporter: Объект User (пользователь, который подал жалобу)
            reported: Объект User (пользователь, на которого пожаловались)
            reported_profile: Объект Profile (профиль пользователя, на которого пожаловались)
            
        Returns:
            Отформатированный текст сообщения
        """
        reporter_username = f"@{reporter.username}" if reporter.username else "нет username"
        reported_username = f"@{reported.username}" if reported.username else "нет username"
        
        # Получение названия причины жалобы
        reason_names = {
            ComplaintReason.ADULT_CONTENT: "18+",
            ComplaintReason.DRUGS: "Наркотики",
            ComplaintReason.FAKE: "Фейк",
            ComplaintReason.HARASSMENT: "Оскорбления",
            ComplaintReason.OTHER: "Другое"
        }
        reason_name = reason_names.get(complaint.reason, complaint.reason)
        
        message = (
            f"🚨 <b>Жалоба {reason_name}</b>\n\n"
            f"👤 <b>Пожаловался:</b>\n"
            f"   ID: {reporter.id}\n"
            f"   Telegram ID: {reporter.telegram_id}\n"
            f"   Username: {reporter_username}\n\n"
            f"👤 <b>На пользователя:</b>\n"
            f"   ID: {reported.id}\n"
            f"   Telegram ID: {reported.telegram_id}\n"
            f"   Username: {reported_username}\n"
        )
        
        if reported_profile:
            message += (
                f"\n📝 <b>Анкета:</b>\n"
                f"   Имя: {reported_profile.name}\n"
                f"   Возраст: {reported_profile.age}\n"
                f"   Пол: {reported_profile.gender}\n"
            )
            if reported_profile.city:
                message += f"   Город: {reported_profile.city}\n"
        
        if complaint.description:
            message += f"\n📄 <b>Описание жалобы:</b>\n{complaint.description}\n"
        
        message += f"\n🆔 <b>ID жалобы:</b> {complaint.id}"
        
        return message
    
    async def ban_user_from_complaint(self, complaint_id: int, moderator_id: int) -> bool:
        """
        Банит пользователя на основе жалобы.
        
        Args:
            complaint_id: ID жалобы
            moderator_id: ID модератора
            
        Returns:
            True если операция успешна, False в противном случае
        """
        try:
            complaint = self.complaint_repo.get_by_id(complaint_id)
            if not complaint:
                logger.error(f"Жалоба {complaint_id} не найдена")
                return False
            
            # Бан пользователя
            self.user_repo.ban_user(complaint.reported_id)
            
            # Обновление статуса жалобы
            self.complaint_repo.update_status(complaint_id, ComplaintStatus.RESOLVED)
            
            # Логирование действия модератора
            self.complaint_repo.add_action(
                complaint_id=complaint_id,
                moderator_id=moderator_id,
                action="ban"
            )
            
            logger.info(f"Пользователь {complaint.reported_id} забанен на основе жалобы {complaint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при бане пользователя из жалобы: {e}", exc_info=True)
            return False
    
    async def dismiss_complaint(self, complaint_id: int, moderator_id: int) -> bool:
        """
        Отклоняет жалобу (не принимает меры).
        
        Args:
            complaint_id: ID жалобы
            moderator_id: ID модератора
            
        Returns:
            True если операция успешна, False в противном случае
        """
        try:
            complaint = self.complaint_repo.get_by_id(complaint_id)
            if not complaint:
                logger.error(f"Жалоба {complaint_id} не найдена")
                return False
            
            # Обновление статуса жалобы
            self.complaint_repo.update_status(complaint_id, ComplaintStatus.DISMISSED)
            
            # Логирование действия модератора
            self.complaint_repo.add_action(
                complaint_id=complaint_id,
                moderator_id=moderator_id,
                action="dismiss"
            )
            
            logger.info(f"Жалоба {complaint_id} отклонена модератором {moderator_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отклонении жалобы: {e}", exc_info=True)
            return False
