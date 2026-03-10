"""
FSM состояния для просмотра анкет.
Используется для отслеживания текущего просматриваемого профиля.
"""
from aiogram.fsm.state import State, StatesGroup


class BrowsingState(StatesGroup):
    """
    Группа состояний для просмотра анкет.
    
    Используется для отслеживания текущего профиля, который просматривает пользователь.
    Это необходимо для работы reply-кнопок, которые не содержат callback_data.
    """
    
    viewing_profile = State()
    """Состояние просмотра анкеты. В data хранится current_profile_id и current_profile_user_id"""
