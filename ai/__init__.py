"""
AI модуль для модерации контента через OpenAI API.
Использует GPT-4o mini для анализа изображений.
"""

from ai.moderation_client import (
    ModerationClient,
    ModerationResult,
    RiskLevel,
    get_moderation_client
)
from ai.nudity_detector import (
    check_nudity,
    is_nsfw,
    requires_manual_review as requires_nudity_review
)
from ai.drug_detector import (
    check_drugs,
    contains_drugs,
    requires_manual_review as requires_drug_review
)

__all__ = [
    # ModerationClient
    "ModerationClient",
    "ModerationResult",
    "RiskLevel",
    "get_moderation_client",
    # Nudity detector
    "check_nudity",
    "is_nsfw",
    "requires_nudity_review",
    # Drug detector
    "check_drugs",
    "contains_drugs",
    "requires_drug_review",
]
