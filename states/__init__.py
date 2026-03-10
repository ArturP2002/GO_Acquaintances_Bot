"""
Модуль FSM состояний для бота знакомств.
Содержит состояния для регистрации, жалоб и редактирования профиля.
"""
from .complaint_state import ComplaintState
from .profile_edit_state import ProfileEditState
from .registration_state import RegistrationState
from .browsing_state import BrowsingState

__all__ = [
    "RegistrationState",
    "ComplaintState",
    "ProfileEditState",
    "BrowsingState",
]
