"""
Репозитории для работы с базой данных.
Слой доступа к данным для всех моделей.
"""
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.repositories.like_repo import LikeRepository
from database.repositories.match_repo import MatchRepository
from database.repositories.complaint_repo import ComplaintRepository
from database.repositories.moderation_repo import ModerationRepository
from database.repositories.boost_repo import BoostRepository
from database.repositories.settings_repo import SettingsRepository
from database.repositories.referral_repo import ReferralRepository

__all__ = [
    "UserRepository",
    "ProfileRepository",
    "LikeRepository",
    "MatchRepository",
    "ComplaintRepository",
    "ModerationRepository",
    "BoostRepository",
    "SettingsRepository",
    "ReferralRepository",
]
