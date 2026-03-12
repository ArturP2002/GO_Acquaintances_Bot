"""
Модели базы данных.
Экспорт всех моделей для удобного импорта.
"""
from database.models.user import BaseModel, User
from database.models.profile import Profile, ProfileMedia
from database.models.like import Like, ProfileView, ProfileHistory
from database.models.match import Match
from database.models.complaint import Complaint, ComplaintAction
from database.models.moderation import ModerationQueue, ModerationAction
from database.models.referral import Referral
from database.models.boost import Boost
from database.models.settings import Settings, AdminUser
from database.models.advertisement import AdvertisementCampaign, AdvertisementMedia

__all__ = [
    # Base
    "BaseModel",
    
    # User
    "User",
    
    # Profile
    "Profile",
    "ProfileMedia",
    
    # Likes and Views
    "Like",
    "ProfileView",
    "ProfileHistory",
    
    # Matches
    "Match",
    
    # Complaints
    "Complaint",
    "ComplaintAction",
    
    # Moderation
    "ModerationQueue",
    "ModerationAction",
    
    # Referrals
    "Referral",
    
    # Boosts
    "Boost",
    
    # Settings and Admin
    "Settings",
    "AdminUser",
    
    # Advertisements
    "AdvertisementCampaign",
    "AdvertisementMedia",
]
