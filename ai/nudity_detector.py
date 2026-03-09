"""
Детектор обнаженного тела и NSFW контента через GPT-4o mini.
"""
import logging
from typing import BinaryIO

from ai.moderation_client import get_moderation_client, ModerationResult, RiskLevel

logger = logging.getLogger(__name__)


async def check_nudity(image_data: bytes | BinaryIO) -> ModerationResult:
    """
    Проверяет изображение на наличие обнаженного тела и NSFW контента.
    
    Args:
        image_data: Данные изображения (bytes или BinaryIO).
    
    Returns:
        ModerationResult с результатом проверки.
        - risk_level: LOW (безопасно), MEDIUM (сомнительно), HIGH (явно NSFW)
        - confidence: Уверенность в результате (0.0-1.0)
        - details: Описание найденных проблем
        - detected_issues: Список найденных проблем
    """
    client = get_moderation_client()
    
    if not client.is_available():
        logger.warning("OpenAI клиент недоступен для проверки на обнаженное тело")
        return ModerationResult(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.0,
            details="AI модерация недоступна - требуется ручная проверка",
            detected_issues=["AI модерация недоступна"]
        )
    
    try:
        result = await client.check_image(
            image_data=image_data,
            check_type="nudity",
            prompt="Проанализируй это изображение на наличие обнаженного тела, "
                   "интимных частей или сексуального контента. Определи уровень риска: "
                   "low - обычное фото в одежде, medium - провокационное фото, "
                   "high - обнаженное тело или явный сексуальный контент."
        )
        
        logger.info(
            f"Проверка на обнаженное тело завершена. "
            f"Уровень риска: {result.risk_level}, уверенность: {result.confidence:.2f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при проверке на обнаженное тело: {e}", exc_info=True)
        return ModerationResult(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.0,
            details=f"Ошибка при проверке: {str(e)}",
            detected_issues=["Ошибка проверки"]
        )


def is_nsfw(result: ModerationResult) -> bool:
    """
    Проверяет, является ли результат проверки NSFW контентом.
    
    Args:
        result: Результат проверки ModerationResult.
    
    Returns:
        True если контент NSFW (MEDIUM или HIGH риск), False иначе.
    """
    return result.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


def requires_manual_review(result: ModerationResult) -> bool:
    """
    Проверяет, требуется ли ручная модерация.
    
    Args:
        result: Результат проверки ModerationResult.
    
    Returns:
        True если требуется ручная проверка, False иначе.
    """
    return result.requires_manual_review()
