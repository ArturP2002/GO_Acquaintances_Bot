"""
Сервис для работы с модерацией профилей.
Отправка анкет в группу модерации, обработка действий модераторов.
"""
import logging
from typing import Optional

from aiogram import Bot

from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.moderation_repo import ModerationRepository
from core.constants import ModerationStatus
from config import config
from keyboards.inline.moderation_keyboard import get_moderation_keyboard
from keyboards.reply.main_menu import get_main_menu_keyboard

# Настройка логирования
logger = logging.getLogger(__name__)


class ModerationService:
    """Сервис для работы с модерацией профилей."""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис модерации.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
        """
        self.bot = bot
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.moderation_repo = ModerationRepository()
        self.moderation_group_id = config.MODERATION_GROUP_ID
    
    async def create_moderation_task(self, user_id: int, profile_id: int, task: str) -> Optional[int]:
        """
        Создает задачу модерации и отправляет анкету в группу модерации.
        
        Args:
            user_id: ID пользователя
            profile_id: ID профиля
            task: Задание для кружка (например, 'Покажи 👍')
            
        Returns:
            ID созданной задачи модерации или None в случае ошибки
        """
        try:
            # Создание задачи модерации
            moderation_task = self.moderation_repo.create(
                user_id=user_id,
                profile_id=profile_id,
                task=task
            )
            
            # Отправка в группу модерации
            await self.send_to_moderation_group(moderation_task.id)
            
            logger.info(f"Задача модерации {moderation_task.id} создана и отправлена в группу")
            return moderation_task.id
            
        except Exception as e:
            logger.error(f"Ошибка при создании задачи модерации: {e}", exc_info=True)
            return None
    
    async def send_to_moderation_group(self, moderation_id: int) -> bool:
        """
        Отправляет анкету в группу модерации с фото, кружком и заданием.
        
        Args:
            moderation_id: ID задачи модерации
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        try:
            logger.info(f"Начало отправки в группу модерации. ID группы: {self.moderation_group_id}, задача: {moderation_id}")
            
            # Получение задачи модерации
            moderation_task = self.moderation_repo.get_by_id(moderation_id)
            if not moderation_task:
                logger.error(f"Задача модерации {moderation_id} не найдена")
                return False
            
            # Получение профиля и пользователя
            profile = self.profile_repo.get_by_id(moderation_task.profile_id)
            if not profile:
                logger.error(f"Профиль {moderation_task.profile_id} не найден")
                return False
            
            user = self.user_repo.get_by_id(moderation_task.user_id)
            if not user:
                logger.error(f"Пользователь {moderation_task.user_id} не найден")
                return False
            
            # Получение медиа профиля
            main_photo = self.profile_repo.get_main_photo(profile.id)
            video_note = self.profile_repo.get_video_note(profile.id)
            
            # Логирование для отладки
            logger.info(f"Медиа для профиля {profile.id}: main_photo={main_photo is not None}, video_note={video_note is not None}")
            if video_note:
                logger.info(f"Video note file_id для профиля {profile.id}: {video_note.video_note_file_id}")
            
            # Формирование текста сообщения
            message_text = self._format_moderation_message(
                user=user,
                profile=profile,
                task=moderation_task.task
            )
            
            # Отправка фото и кружка
            if main_photo and main_photo.photo_file_id:
                # Сначала отправляем кружок, если он есть
                if video_note and video_note.video_note_file_id:
                    try:
                        logger.info(f"Отправка кружка в группу модерации {self.moderation_group_id} для задачи {moderation_id}")
                        await self.bot.send_video_note(
                            chat_id=self.moderation_group_id,
                            video_note=video_note.video_note_file_id
                        )
                        logger.info(f"Кружок успешно отправлен в группу модерации для задачи {moderation_id}")
                    except Exception as video_note_error:
                        logger.error(
                            f"Ошибка при отправке кружка в группу модерации для задачи {moderation_id}: {video_note_error}",
                            exc_info=True
                        )
                        # Продолжаем выполнение, даже если кружок не отправился
                
                # Затем отправляем фото с текстом
                await self.bot.send_photo(
                    chat_id=self.moderation_group_id,
                    photo=main_photo.photo_file_id,
                    caption=message_text,
                    parse_mode="HTML",
                    reply_markup=get_moderation_keyboard(moderation_id)
                )
            elif video_note and video_note.video_note_file_id:
                # Если нет фото, но есть кружок, отправляем только кружок
                try:
                    logger.info(f"Отправка кружка в группу модерации {self.moderation_group_id} для задачи {moderation_id}")
                    await self.bot.send_video_note(
                        chat_id=self.moderation_group_id,
                        video_note=video_note.video_note_file_id
                    )
                    logger.info(f"Кружок успешно отправлен в группу модерации для задачи {moderation_id}")
                except Exception as video_note_error:
                    logger.error(
                        f"Ошибка при отправке кружка в группу модерации для задачи {moderation_id}: {video_note_error}",
                        exc_info=True
                    )
                    # Продолжаем выполнение, даже если кружок не отправился
                
                # Отправляем текст отдельным сообщением
                await self.bot.send_message(
                    chat_id=self.moderation_group_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=get_moderation_keyboard(moderation_id)
                )
            else:
                # Если нет ни фото, ни кружка, отправляем только текст
                await self.bot.send_message(
                    chat_id=self.moderation_group_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=get_moderation_keyboard(moderation_id)
                )
            
            logger.info(f"Анкета отправлена в группу модерации для задачи {moderation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке анкеты в группу модерации: {e}", exc_info=True)
            return False
    
    def _format_moderation_message(self, user, profile, task: str) -> str:
        """
        Формирует текст сообщения для модерации.
        
        Args:
            user: Объект User
            profile: Объект Profile
            task: Задание для кружка
            
        Returns:
            Отформатированный текст сообщения
        """
        username = f"@{user.username}" if user.username else "нет username"
        
        message = (
            f"📋 <b>Новая анкета на модерацию</b>\n\n"
            f"👤 <b>Пользователь:</b>\n"
            f"   ID: {user.id}\n"
            f"   Telegram ID: {user.telegram_id}\n"
            f"   Username: {username}\n\n"
            f"📝 <b>Анкета:</b>\n"
            f"   Имя: {profile.name}\n"
            f"   Возраст: {profile.age}\n"
            f"   Пол: {profile.gender}\n"
        )
        
        if profile.city:
            message += f"   Город: {profile.city}\n"
        
        if profile.bio:
            message += f"\n📄 <b>Описание:</b>\n{profile.bio}\n"
        
        message += f"\n🎯 <b>Задание для кружка:</b> {task}\n"
        message += f"\n🆔 <b>ID модерации:</b> {profile.id}"
        
        return message
    
    async def approve_profile(self, moderation_id: int, moderator_id: int, 
                             comment: Optional[str] = None) -> bool:
        """
        Одобряет профиль после модерации.
        
        Args:
            moderation_id: ID задачи модерации
            moderator_id: ID модератора
            comment: Комментарий модератора (опционально)
            
        Returns:
            True если операция успешна, False в противном случае
        """
        try:
            # Получение задачи модерации
            moderation_task = self.moderation_repo.get_by_id(moderation_id)
            if not moderation_task:
                logger.error(f"Задача модерации {moderation_id} не найдена")
                return False
            
            # Обновление статуса задачи
            self.moderation_repo.update_status(moderation_id, ModerationStatus.APPROVED)
            
            # Верификация пользователя
            self.user_repo.verify_user(moderation_task.user_id)
            
            # Логирование действия модератора
            self.moderation_repo.add_action(
                moderation_id=moderation_id,
                moderator_id=moderator_id,
                action="approve",
                comment=comment
            )
            
            # Уведомление пользователя
            user = self.user_repo.get_by_id(moderation_task.user_id)
            if user:
                try:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text="✅ Ваша анкета одобрена модератором! Теперь вы можете пользоваться ботом.",
                        reply_markup=get_main_menu_keyboard()
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")
            
            logger.info(f"Профиль {moderation_task.profile_id} одобрен модератором {moderator_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при одобрении профиля: {e}", exc_info=True)
            return False
    
    async def reject_profile(self, moderation_id: int, moderator_id: int,
                             comment: Optional[str] = None) -> bool:
        """
        Отклоняет профиль после модерации.
        
        Args:
            moderation_id: ID задачи модерации
            moderator_id: ID модератора
            comment: Комментарий модератора (опционально)
            
        Returns:
            True если операция успешна, False в противном случае
        """
        try:
            # Получение задачи модерации
            moderation_task = self.moderation_repo.get_by_id(moderation_id)
            if not moderation_task:
                logger.error(f"Задача модерации {moderation_id} не найдена")
                return False
            
            # Обновление статуса задачи
            self.moderation_repo.update_status(moderation_id, ModerationStatus.REJECTED)
            
            # Логирование действия модератора
            self.moderation_repo.add_action(
                moderation_id=moderation_id,
                moderator_id=moderator_id,
                action="reject",
                comment=comment
            )
            
            # Уведомление пользователя
            user = self.user_repo.get_by_id(moderation_task.user_id)
            if user:
                try:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text="❌ Ваша анкета отклонена модератором. Пожалуйста, загрузите кружок заново, выполнив задание корректно."
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")
            
            logger.info(f"Профиль {moderation_task.profile_id} отклонен модератором {moderator_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отклонении профиля: {e}", exc_info=True)
            return False
    
    async def ban_user(self, moderation_id: int, moderator_id: int,
                      comment: Optional[str] = None) -> bool:
        """
        Банит пользователя после модерации.
        
        Args:
            moderation_id: ID задачи модерации
            moderator_id: ID модератора
            comment: Комментарий модератора (опционально)
            
        Returns:
            True если операция успешна, False в противном случае
        """
        try:
            # Получение задачи модерации
            moderation_task = self.moderation_repo.get_by_id(moderation_id)
            if not moderation_task:
                logger.error(f"Задача модерации {moderation_id} не найдена")
                return False
            
            # Обновление статуса задачи
            self.moderation_repo.update_status(moderation_id, ModerationStatus.BANNED)
            
            # Бан пользователя
            self.user_repo.ban_user(moderation_task.user_id)
            
            # Логирование действия модератора
            self.moderation_repo.add_action(
                moderation_id=moderation_id,
                moderator_id=moderator_id,
                action="ban",
                comment=comment
            )
            
            # Уведомление пользователя
            user = self.user_repo.get_by_id(moderation_task.user_id)
            if user:
                try:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text="🚫 Вы были забанены модератором. Если вы считаете, что это ошибка, свяжитесь с поддержкой."
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")
            
            logger.info(f"Пользователь {moderation_task.user_id} забанен модератором {moderator_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при бане пользователя: {e}", exc_info=True)
            return False
