"""
Сервис для проверки профиля через ИИ при редактировании.
Проверяет все категории контента: nudity, drugs, violence, general.
"""
import logging
from typing import Optional, Dict, Any
from aiogram import Bot

from services.ai_moderation_service import AIModerationService
from ai.moderation_client import ModerationResult, RiskLevel
from database.repositories.profile_repo import ProfileRepository
from database.repositories.user_repo import UserRepository
from config import config

logger = logging.getLogger(__name__)


class AIProfileChecker:
    """
    Сервис для проверки профиля через ИИ при редактировании.
    """
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис проверки профиля.
        
        Args:
            bot: Экземпляр бота для работы с файлами
        """
        self.bot = bot
        self.ai_service = AIModerationService(bot)
        self.profile_repo = ProfileRepository()
        self.user_repo = UserRepository()
        from ai.moderation_client import get_moderation_client
        self.moderation_client = get_moderation_client()
    
    async def check_profile_content(
        self,
        user_id: int,
        field_type: str,
        content: Optional[str] = None,
        photo_file_id: Optional[str] = None
    ) -> Optional[ModerationResult]:
        """
        Проверяет контент профиля через ИИ при редактировании.
        
        Args:
            user_id: ID пользователя
            field_type: Тип поля (name, age, gender, city, bio, photo)
            content: Текстовый контент (для текстовых полей)
            photo_file_id: File ID фото (для поля photo)
            
        Returns:
            ModerationResult если найдены нарушения, None если все в порядке
        """
        if not self.ai_service.is_available():
            logger.debug("AI модерация недоступна, пропускаем проверку")
            return None
        
        try:
            # Для фото проверяем через ИИ
            if field_type == "photo" and photo_file_id:
                # Проверяем все типы отдельно, чтобы определить конкретный тип нарушения
                results = {}
                check_types = ["nudity", "drugs", "violence", "general"]
                
                for check_type in check_types:
                    try:
                        if check_type == "nudity":
                            result = await self.ai_service.check_photo_nudity(photo_file_id)
                        elif check_type == "drugs":
                            result = await self.ai_service.check_photo_drugs(photo_file_id)
                        elif check_type == "violence":
                            result = await self.ai_service.check_photo_violence(photo_file_id)
                        else:
                            result = await self.ai_service.check_photo(photo_file_id)
                        
                        if result.requires_manual_review():
                            results[check_type] = result
                    except Exception as e:
                        logger.warning(f"Ошибка при проверке типа {check_type}: {e}")
                        continue
                
                # Если есть нарушения, возвращаем результат с максимальным риском
                if results:
                    # Находим результат с максимальным уровнем риска
                    max_risk_result = max(results.values(), key=lambda r: (
                        2 if r.risk_level == RiskLevel.HIGH else
                        1 if r.risk_level == RiskLevel.MEDIUM else 0
                    ))
                    
                    # Определяем тип нарушения
                    max_risk_type = max(results.keys(), key=lambda k: (
                        2 if results[k].risk_level == RiskLevel.HIGH else
                        1 if results[k].risk_level == RiskLevel.MEDIUM else 0
                    ))
                    
                    # Сохраняем тип нарушения в detected_issues для последующего использования
                    max_risk_result.detected_issues.append(f"violation_type:{max_risk_type}")
                    
                    return max_risk_result
                
                return None
            
            # Для текстовых полей (bio) проверяем через OpenAI Moderation API
            if field_type == "bio" and content:
                try:
                    result = await self.moderation_client.check_text(
                        text=content,
                        check_type="general"
                    )
                    return result if result.requires_manual_review() else None
                except Exception as e:
                    logger.warning(f"Ошибка при проверке текста: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке профиля через ИИ: {e}", exc_info=True)
            return None
    
    async def handle_ai_moderation_result(
        self,
        user_id: int,
        result: ModerationResult,
        field_type: str,
        check_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Обрабатывает результат проверки ИИ и принимает решение.
        
        Args:
            user_id: ID пользователя
            result: Результат проверки ИИ
            field_type: Тип поля профиля
            check_type: Тип нарушения (nudity, drugs, violence, general)
            
        Returns:
            Словарь с информацией о действии:
            {
                'action': 'ban' | 'notify' | 'allow',
                'message': str,
                'should_notify_admin': bool
            }
        """
        if result.risk_level == RiskLevel.HIGH:
            # Высокий риск - автоматически баним, но уведомляем админов
            try:
                user = self.user_repo.get_by_id(user_id)
                if user and not user.is_banned:
                    self.user_repo.ban_user(user_id)
                    logger.warning(
                        f"Пользователь {user_id} забанен автоматически ИИ "
                        f"за нарушение типа {check_type} (confidence: {result.confidence:.2f})"
                    )
                
                return {
                    'action': 'ban',
                    'message': (
                        f"🚫 Ваш аккаунт был заблокирован автоматически "
                        f"из-за обнаружения запрещенного контента.\n\n"
                        f"Тип нарушения: {check_type}\n"
                        f"Детали: {result.details or 'Запрещенный контент'}\n\n"
                        f"Если вы считаете, что это ошибка, свяжитесь с поддержкой."
                    ),
                    'should_notify_admin': True,
                    'auto_banned': True
                }
            except Exception as e:
                logger.error(f"Ошибка при автоматическом бане пользователя {user_id}: {e}", exc_info=True)
                # В случае ошибки все равно уведомляем админов
                return {
                    'action': 'notify',
                    'message': None,
                    'should_notify_admin': True,
                    'auto_banned': False
                }
        
        elif result.risk_level == RiskLevel.MEDIUM:
            # Средний риск - уведомляем админов для ручной проверки
            return {
                'action': 'notify',
                'message': None,
                'should_notify_admin': True,
                'auto_banned': False
            }
        
        else:
            # Низкий риск - все в порядке
            return {
                'action': 'allow',
                'message': None,
                'should_notify_admin': False,
                'auto_banned': False
            }
    
    def format_admin_notification(
        self,
        user_id: int,
        result: ModerationResult,
        check_type: str,
        field_type: str,
        auto_banned: bool = False
    ) -> str:
        """
        Форматирует уведомление для админов.
        
        Args:
            user_id: ID пользователя
            result: Результат проверки ИИ
            check_type: Тип нарушения
            field_type: Тип поля профиля
            auto_banned: Был ли пользователь автоматически забанен
            
        Returns:
            Отформатированный текст уведомления
        """
        risk_emoji = "🔴" if result.risk_level == RiskLevel.HIGH else "🟡"
        auto_ban_text = "\n\n🚫 Пользователь автоматически забанен" if auto_banned else ""
        
        notification = (
            f"⚠️ <b>Возможный запрещённый контент</b>\n\n"
            f"User ID: {user_id}\n"
            f"Confidence: {int(result.confidence * 100)}%\n"
            f"Тип: {check_type}\n"
            f"Поле: {field_type}\n"
            f"Уровень риска: {risk_emoji} {result.risk_level.upper()}\n"
        )
        
        if result.details:
            notification += f"\nДетали: {result.details}\n"
        
        if result.detected_issues:
            # Фильтруем violation_type из списка для отображения
            display_issues = [issue for issue in result.detected_issues if not issue.startswith("violation_type:")]
            if display_issues:
                notification += f"\nОбнаружено: {', '.join(display_issues)}\n"
        
        notification += auto_ban_text
        
        return notification
    
    async def send_profile_to_admins(
        self,
        user_id: int,
        result: ModerationResult,
        check_type: str,
        field_type: str,
        auto_banned: bool = False
    ) -> bool:
        """
        Отправляет полную анкету пользователя в группу админов для проверки решения ИИ.
        
        Args:
            user_id: ID пользователя
            result: Результат проверки ИИ
            check_type: Тип нарушения
            field_type: Тип поля профиля
            auto_banned: Был ли пользователь автоматически забанен
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        try:
            from config import config
            from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
            from keyboards.inline.moderation_keyboard import get_ai_decision_keyboard
            
            if not config.ADMIN_GROUP_ID:
                logger.warning("ADMIN_GROUP_ID не установлен, пропускаем отправку анкеты")
                return False
            
            logger.info(f"Начало отправки анкеты пользователя {user_id} в группу админов {config.ADMIN_GROUP_ID}")
            
            # Получаем пользователя и профиль
            user = self.user_repo.get_by_id(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден для отправки анкеты админам")
                return False
            
            profile = self.profile_repo.get_by_user_id(user.id)
            if not profile:
                logger.error(f"Профиль для пользователя {user_id} не найден")
                return False
            
            # Форматируем текст анкеты
            username = f"@{user.username}" if user.username else "нет username"
            profile_text = (
                f"📋 <b>Обновленная анкета после проверки ИИ</b>\n\n"
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
                profile_text += f"   Город: {profile.city}\n"
            
            if profile.bio:
                profile_text += f"\n📄 <b>Описание:</b>\n{profile.bio}\n"
            
            # Добавляем информацию о решении ИИ
            risk_emoji = "🔴" if result.risk_level == RiskLevel.HIGH else "🟡"
            auto_ban_text = "\n🚫 <b>Пользователь автоматически забанен</b>" if auto_banned else ""
            
            profile_text += (
                f"\n\n🤖 <b>Решение ИИ:</b>\n"
                f"   Confidence: {int(result.confidence * 100)}%\n"
                f"   Тип нарушения: {check_type}\n"
                f"   Уровень риска: {risk_emoji} {result.risk_level.upper()}\n"
                f"{auto_ban_text}"
            )
            
            if result.details:
                profile_text += f"\n📋 <b>Детали:</b> {result.details}\n"
            
            # Получаем фото профиля
            photo_file_id = get_profile_photo_file_id(profile)
            logger.debug(f"Фото профиля для пользователя {user_id}: {'найдено' if photo_file_id else 'не найдено'}")
            
            # Создаем клавиатуру с кнопками оценки решения ИИ
            keyboard = get_ai_decision_keyboard(user.id, check_type)
            
            # Отправляем анкету
            try:
                if photo_file_id:
                    logger.debug(f"Отправка анкеты с фото в группу {config.ADMIN_GROUP_ID}")
                    await self.bot.send_photo(
                        chat_id=config.ADMIN_GROUP_ID,
                        photo=photo_file_id,
                        caption=profile_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    logger.debug(f"Отправка анкеты без фото в группу {config.ADMIN_GROUP_ID}")
                    await self.bot.send_message(
                        chat_id=config.ADMIN_GROUP_ID,
                        text=profile_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                
                logger.info(f"Анкета пользователя {user_id} успешно отправлена админам для проверки решения ИИ")
                return True
            except Exception as send_error:
                logger.error(f"Ошибка при отправке анкеты в группу админов: {send_error}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при отправке анкеты админам: {e}", exc_info=True)
            return False
    
    async def send_profile_to_admins_safe(
        self,
        user_id: int,
        field_type: str
    ) -> bool:
        """
        Отправляет полную анкету пользователя в группу админов без информации о нарушениях ИИ.
        Используется когда ИИ не нашел нарушений или недоступен.
        
        Args:
            user_id: ID пользователя
            field_type: Тип поля профиля
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        try:
            from config import config
            from utils.profile_formatter import format_profile_text, get_profile_photo_file_id
            from keyboards.inline.moderation_keyboard import get_ai_decision_keyboard
            
            if not config.ADMIN_GROUP_ID:
                logger.warning("ADMIN_GROUP_ID не установлен, пропускаем отправку анкеты")
                return False
            
            logger.info(f"Начало отправки анкеты пользователя {user_id} в группу админов {config.ADMIN_GROUP_ID} (без нарушений)")
            
            # Получаем пользователя и профиль
            user = self.user_repo.get_by_id(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден для отправки анкеты админам")
                return False
            
            profile = self.profile_repo.get_by_user_id(user.id)
            if not profile:
                logger.error(f"Профиль для пользователя {user_id} не найден")
                return False
            
            # Форматируем текст анкеты
            username = f"@{user.username}" if user.username else "нет username"
            profile_text = (
                f"📋 <b>Обновленная анкета</b>\n\n"
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
                profile_text += f"   Город: {profile.city}\n"
            
            if profile.bio:
                profile_text += f"\n📄 <b>Описание:</b>\n{profile.bio}\n"
            
            profile_text += (
                f"\n\n🤖 <b>Проверка ИИ:</b>\n"
                f"   ✅ Нарушений не обнаружено\n"
                f"   Поле: {field_type}\n"
            )
            
            # Получаем фото профиля
            photo_file_id = get_profile_photo_file_id(profile)
            logger.debug(f"Фото профиля для пользователя {user_id}: {'найдено' if photo_file_id else 'не найдено'}")
            
            # Создаем клавиатуру с кнопками оценки решения ИИ
            from keyboards.inline.moderation_keyboard import get_ai_decision_keyboard
            keyboard = get_ai_decision_keyboard(user.id, "general")
            
            # Отправляем анкету
            try:
                if photo_file_id:
                    logger.debug(f"Отправка анкеты с фото в группу {config.ADMIN_GROUP_ID}")
                    await self.bot.send_photo(
                        chat_id=config.ADMIN_GROUP_ID,
                        photo=photo_file_id,
                        caption=profile_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    logger.debug(f"Отправка анкеты без фото в группу {config.ADMIN_GROUP_ID}")
                    await self.bot.send_message(
                        chat_id=config.ADMIN_GROUP_ID,
                        text=profile_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                
                logger.info(f"Анкета пользователя {user_id} успешно отправлена админам (без нарушений)")
                return True
            except Exception as send_error:
                logger.error(f"Ошибка при отправке анкеты в группу админов: {send_error}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при отправке анкеты админам: {e}", exc_info=True)
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при отправке анкеты админам: {e}", exc_info=True)
            return False