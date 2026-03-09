"""
FSM состояния для редактирования профиля пользователя.
Используется для изменения данных анкеты.
"""
from aiogram.fsm.state import State, StatesGroup


class ProfileEditState(StatesGroup):
    """
    Группа состояний для редактирования профиля.
    
    Состояния для изменения различных полей профиля:
    - name - редактирование имени
    - age - редактирование возраста
    - gender - редактирование пола
    - city - редактирование города
    - bio - редактирование описания
    - photo - замена фото
    - video_note - замена кружка
    - min_age_preference - изменение минимального возраста для поиска
    - max_age_preference - изменение максимального возраста для поиска
    """
    
    editing_name = State()
    """Редактирование имени"""
    
    editing_age = State()
    """Редактирование возраста"""
    
    editing_gender = State()
    """Редактирование пола"""
    
    editing_city = State()
    """Редактирование города"""
    
    editing_bio = State()
    """Редактирование описания (био)"""
    
    editing_photo = State()
    """Замена фото"""
    
    editing_video_note = State()
    """Замена кружка (video note)"""
    
    editing_min_age_preference = State()
    """Изменение минимального возраста для поиска"""
    
    editing_max_age_preference = State()
    """Изменение максимального возраста для поиска"""
