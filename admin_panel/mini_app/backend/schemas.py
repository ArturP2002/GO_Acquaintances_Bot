"""
Pydantic схемы для валидации данных в API.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from core.constants import ComplaintStatus, ComplaintReason, AdminRole


# User schemas
class UserBase(BaseModel):
    """Базовая схема пользователя."""
    telegram_id: int
    username: Optional[str] = None
    is_banned: bool = False
    is_verified: bool = False
    is_active: bool = True
    last_active: Optional[datetime] = None


class UserResponse(UserBase):
    """Схема ответа с данными пользователя."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Схема для обновления пользователя."""
    is_banned: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class UserSearch(BaseModel):
    """Схема для поиска пользователей."""
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    is_banned: Optional[bool] = None
    is_verified: Optional[bool] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class UserListResponse(BaseModel):
    """Схема ответа со списком пользователей."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


# Profile schemas
class ProfileResponse(BaseModel):
    """Схема ответа с данными профиля."""
    id: int
    user_id: int
    name: str
    age: int
    gender: str
    city: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Complaint schemas
class ComplaintBase(BaseModel):
    """Базовая схема жалобы."""
    reported_id: int
    reason: str = Field(..., description="Причина жалобы")
    description: Optional[str] = None


class ComplaintResponse(BaseModel):
    """Схема ответа с данными жалобы."""
    id: int
    reporter_id: int
    reported_id: int
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComplaintUpdate(BaseModel):
    """Схема для обновления жалобы."""
    status: str
    comment: Optional[str] = None


class ComplaintListResponse(BaseModel):
    """Схема ответа со списком жалоб."""
    complaints: List[ComplaintResponse]
    total: int
    page: int
    page_size: int


# Settings schemas
class SettingResponse(BaseModel):
    """Схема ответа с настройкой."""
    id: int
    key: str
    value: str
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """Схема для обновления настройки."""
    value: str


# Boost schemas
class BoostResponse(BaseModel):
    """Схема ответа с данными буста."""
    id: int
    user_id: int
    boost_value: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BoostCreate(BaseModel):
    """Схема для создания буста."""
    user_id: int
    boost_value: int = Field(..., ge=1, description="Значение буста")
    expires_at: Optional[datetime] = None


class BoostListResponse(BaseModel):
    """Схема ответа со списком бустов."""
    boosts: List[BoostResponse]
    total: int


# Admin schemas
class AdminUserResponse(BaseModel):
    """Схема ответа с данными администратора."""
    id: int
    user_id: int
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Stats schemas
class StatsResponse(BaseModel):
    """Схема ответа со статистикой."""
    totalUsers: int
    totalProfiles: int
    totalLikes: int
    totalMatches: int
    bannedUsers: int
    verifiedUsers: int
    pendingComplaints: int


# Test profiles schemas
class TestProfilesCountResponse(BaseModel):
    """Схема ответа с количеством тестовых анкет."""
    count: int


class DeleteTestProfilesResponse(BaseModel):
    """Схема ответа при удалении тестовых анкет."""
    message: str
    deleted_count: int
