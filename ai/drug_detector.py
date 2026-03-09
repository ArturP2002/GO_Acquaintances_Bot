"""
Детектор наркотических веществ через GPT-4o mini.
"""
import logging
from typing import BinaryIO

from ai.moderation_client import get_moderation_client, ModerationResult, RiskLevel

logger = logging.getLogger(__name__)


async def check_drugs(image_data: bytes | BinaryIO) -> ModerationResult:
    """
    Проверяет изображение на наличие наркотических веществ.
    
    Args:
        image_data: Данные изображения (bytes или BinaryIO).
    
    Returns:
        ModerationResult с результатом проверки.
        - risk_level: LOW (безопасно), MEDIUM (сомнительно), HIGH (явно наркотики)
        - confidence: Уверенность в результате (0.0-1.0)
        - details: Описание найденных проблем
        - detected_issues: Список найденных проблем
    """
    client = get_moderation_client()
    
    if not client.is_available():
        logger.warning("OpenAI клиент недоступен для проверки на наркотики")
        return ModerationResult(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.0,
            details="AI модерация недоступна - требуется ручная проверка",
            detected_issues=["AI модерация недоступна"]
        )
    
    try:
        result = await client.check_image(
            image_data=image_data,
            check_type="drugs",
            prompt="Проанализируй это изображение на наличие наркотических веществ, "
                   "наркотиков, сигарет или алкоголя в неуместном контексте. "
                   "Определи уровень риска: "
                   "low - обычное фото без запрещенных веществ, "
                   "medium - возможно присутствие наркотиков или провокационный контент, "
                   "high - явные наркотики или употребление наркотиков."
        )
        
        logger.info(
            f"Проверка на наркотики завершена. "
            f"Уровень риска: {result.risk_level}, уверенность: {result.confidence:.2f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при проверке на наркотики: {e}", exc_info=True)
        return ModerationResult(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.0,
            details=f"Ошибка при проверке: {str(e)}",
            detected_issues=["Ошибка проверки"]
        )


def contains_drugs(result: ModerationResult) -> bool:
    """
    Проверяет, содержит ли изображение наркотики.
    
    Args:
        result: Результат проверки ModerationResult.
    
    Returns:
        True если обнаружены наркотики (MEDIUM или HIGH риск), False иначе.
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
