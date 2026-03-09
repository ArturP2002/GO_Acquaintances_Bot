"""
Сервис для AI модерации контента через OpenAI API.
Использует GPT-4o mini для проверки фото на запрещенный контент.
"""
import logging
import io
from typing import Optional

from aiogram import Bot
from aiogram.types import PhotoSize

from ai.moderation_client import get_moderation_client, ModerationResult, RiskLevel
from ai.nudity_detector import check_nudity
from ai.drug_detector import check_drugs

logger = logging.getLogger(__name__)


class AIModerationService:
    """
    Сервис для AI модерации контента.
    Использует OpenAI API (GPT-4o mini) для проверки фото на запрещенный контент.
    """
    
    def __init__(self, bot: Bot):
        """
        Инициализирует сервис AI модерации.
        
        Args:
            bot: Экземпляр бота для загрузки файлов из Telegram
        """
        self.bot = bot
        self.moderation_client = get_moderation_client()
    
    def is_available(self) -> bool:
        """
        Проверяет, доступен ли AI модерация.
        
        Returns:
            True если OpenAI API доступен, False иначе
        """
        return self.moderation_client.is_available()
    
    async def check_photo(
        self,
        photo_file_id: str,
        check_types: Optional[list[str]] = None
    ) -> ModerationResult:
        """
        Проверяет фото на наличие запрещенного контента.
        
        Args:
            photo_file_id: File ID фото в Telegram
            check_types: Список типов проверки: ["nudity", "drugs", "violence", "general"]
                       Если None, выполняется общая проверка
        
        Returns:
            ModerationResult с результатом проверки:
            - risk_level: LOW (безопасно), MEDIUM (сомнительно), HIGH (явно запрещено)
            - confidence: Уверенность в результате (0.0-1.0)
            - details: Описание найденных проблем
            - detected_issues: Список найденных проблем
        """
        if not self.is_available():
            logger.warning("AI модерация недоступна - требуется ручная проверка")
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details="AI модерация недоступна - требуется ручная проверка",
                detected_issues=["AI модерация недоступна"]
            )
        
        try:
            # Загрузка фото из Telegram
            image_data = await self._download_photo(photo_file_id)
            if not image_data:
                logger.error(f"Не удалось загрузить фото {photo_file_id}")
                return ModerationResult(
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.0,
                    details="Не удалось загрузить фото для проверки",
                    detected_issues=["Ошибка загрузки"]
                )
            
            # Если указаны конкретные типы проверки, выполняем их
            if check_types:
                return await self._check_multiple_types(image_data, check_types)
            
            # Общая проверка на все виды запрещенного контента
            return await self._check_general(image_data)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке фото через AI: {e}", exc_info=True)
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details=f"Ошибка при проверке: {str(e)}",
                detected_issues=["Ошибка проверки"]
            )
    
    async def check_photo_nudity(self, photo_file_id: str) -> ModerationResult:
        """
        Проверяет фото на наличие обнаженного тела и NSFW контента.
        
        Args:
            photo_file_id: File ID фото в Telegram
        
        Returns:
            ModerationResult с результатом проверки на обнаженное тело
        """
        if not self.is_available():
            logger.warning("AI модерация недоступна для проверки на обнаженное тело")
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details="AI модерация недоступна - требуется ручная проверка",
                detected_issues=["AI модерация недоступна"]
            )
        
        try:
            image_data = await self._download_photo(photo_file_id)
            if not image_data:
                logger.error(f"Не удалось загрузить фото {photo_file_id}")
                return ModerationResult(
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.0,
                    details="Не удалось загрузить фото для проверки",
                    detected_issues=["Ошибка загрузки"]
                )
            
            return await check_nudity(image_data)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке на обнаженное тело: {e}", exc_info=True)
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details=f"Ошибка при проверке: {str(e)}",
                detected_issues=["Ошибка проверки"]
            )
    
    async def check_photo_drugs(self, photo_file_id: str) -> ModerationResult:
        """
        Проверяет фото на наличие наркотических веществ.
        
        Args:
            photo_file_id: File ID фото в Telegram
        
        Returns:
            ModerationResult с результатом проверки на наркотики
        """
        if not self.is_available():
            logger.warning("AI модерация недоступна для проверки на наркотики")
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details="AI модерация недоступна - требуется ручная проверка",
                detected_issues=["AI модерация недоступна"]
            )
        
        try:
            image_data = await self._download_photo(photo_file_id)
            if not image_data:
                logger.error(f"Не удалось загрузить фото {photo_file_id}")
                return ModerationResult(
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.0,
                    details="Не удалось загрузить фото для проверки",
                    detected_issues=["Ошибка загрузки"]
                )
            
            return await check_drugs(image_data)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке на наркотики: {e}", exc_info=True)
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details=f"Ошибка при проверке: {str(e)}",
                detected_issues=["Ошибка проверки"]
            )
    
    async def check_photo_violence(self, photo_file_id: str) -> ModerationResult:
        """
        Проверяет фото на наличие насилия, оружия и агрессии.
        
        Args:
            photo_file_id: File ID фото в Telegram
        
        Returns:
            ModerationResult с результатом проверки на насилие
        """
        if not self.is_available():
            logger.warning("AI модерация недоступна для проверки на насилие")
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details="AI модерация недоступна - требуется ручная проверка",
                detected_issues=["AI модерация недоступна"]
            )
        
        try:
            image_data = await self._download_photo(photo_file_id)
            if not image_data:
                logger.error(f"Не удалось загрузить фото {photo_file_id}")
                return ModerationResult(
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.0,
                    details="Не удалось загрузить фото для проверки",
                    detected_issues=["Ошибка загрузки"]
                )
            
            return await self.moderation_client.check_image(
                image_data=image_data,
                check_type="violence",
                prompt="Проанализируй это изображение на наличие насилия, оружия или агрессии. "
                       "Определи уровень риска: "
                       "low - обычное фото без насилия, "
                       "medium - возможно присутствие оружия или агрессивный контент, "
                       "high - явное насилие, оружие или агрессивные действия."
            )
            
        except Exception as e:
            logger.error(f"Ошибка при проверке на насилие: {e}", exc_info=True)
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details=f"Ошибка при проверке: {str(e)}",
                detected_issues=["Ошибка проверки"]
            )
    
    async def _download_photo(self, photo_file_id: str) -> Optional[bytes]:
        """
        Загружает фото из Telegram по file_id.
        
        Args:
            photo_file_id: File ID фото в Telegram
        
        Returns:
            Данные изображения в виде bytes или None в случае ошибки
        """
        try:
            # Получение информации о файле
            file = await self.bot.get_file(photo_file_id)
            
            # Загрузка файла в память
            file_data = io.BytesIO()
            await self.bot.download_file(file.file_path, destination=file_data)
            
            # Получение bytes из BytesIO
            file_data.seek(0)
            image_bytes = file_data.read()
            
            logger.debug(f"Фото {photo_file_id} успешно загружено, размер: {len(image_bytes)} байт")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке фото {photo_file_id}: {e}", exc_info=True)
            return None
    
    async def _check_general(self, image_data: bytes) -> ModerationResult:
        """
        Выполняет общую проверку фото на все виды запрещенного контента.
        
        Args:
            image_data: Данные изображения в виде bytes
        
        Returns:
            ModerationResult с результатом проверки
        """
        return await self.moderation_client.check_image(
            image_data=image_data,
            check_type="general",
            prompt="Проанализируй это изображение на наличие любого запрещенного контента: "
                   "обнаженное тело, наркотики, насилие, оружие, запрещенные символы. "
                   "Определи уровень риска: "
                   "low - безопасный контент, "
                   "medium - сомнительный контент, требующий проверки, "
                   "high - явно запрещенный контент."
        )
    
    async def _check_multiple_types(
        self,
        image_data: bytes,
        check_types: list[str]
    ) -> ModerationResult:
        """
        Выполняет проверку фото по нескольким типам и возвращает максимальный риск.
        
        Args:
            image_data: Данные изображения в виде bytes
            check_types: Список типов проверки
        
        Returns:
            ModerationResult с максимальным уровнем риска из всех проверок
        """
        results = []
        
        for check_type in check_types:
            try:
                if check_type == "nudity":
                    result = await check_nudity(image_data)
                elif check_type == "drugs":
                    result = await check_drugs(image_data)
                elif check_type == "violence":
                    result = await self.moderation_client.check_image(
                        image_data=image_data,
                        check_type="violence"
                    )
                else:
                    result = await self.moderation_client.check_image(
                        image_data=image_data,
                        check_type=check_type
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Ошибка при проверке типа {check_type}: {e}")
                # В случае ошибки добавляем средний уровень риска
                results.append(ModerationResult(
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.0,
                    details=f"Ошибка при проверке {check_type}",
                    detected_issues=[f"Ошибка проверки {check_type}"]
                ))
        
        # Определение максимального уровня риска
        risk_levels = [result.risk_level for result in results]
        if RiskLevel.HIGH in risk_levels:
            max_risk = RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risk_levels:
            max_risk = RiskLevel.MEDIUM
        else:
            max_risk = RiskLevel.LOW
        
        # Объединение всех найденных проблем
        all_issues = []
        all_details = []
        max_confidence = 0.0
        
        for result in results:
            if result.detected_issues:
                all_issues.extend(result.detected_issues)
            if result.details:
                all_details.append(result.details)
            if result.confidence > max_confidence:
                max_confidence = result.confidence
        
        return ModerationResult(
            risk_level=max_risk,
            confidence=max_confidence,
            details="; ".join(all_details) if all_details else "Проверка завершена",
            detected_issues=list(set(all_issues))  # Удаление дубликатов
        )
    
    def should_send_to_moderation(self, result: ModerationResult) -> bool:
        """
        Определяет, нужно ли отправлять контент на ручную модерацию.
        
        Args:
            result: Результат AI проверки
        
        Returns:
            True если требуется ручная модерация (MEDIUM или HIGH риск), False иначе
        """
        return result.requires_manual_review()
    
    def is_safe(self, result: ModerationResult) -> bool:
        """
        Проверяет, является ли контент безопасным.
        
        Args:
            result: Результат AI проверки
        
        Returns:
            True если контент безопасен (LOW риск), False иначе
        """
        return result.is_safe()
