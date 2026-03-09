"""
FSM состояния для процесса регистрации пользователя.
Используется для пошагового сбора данных анкеты.
"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    """
    Группа состояний для регистрации нового пользователя.
    
    Последовательность состояний:
    1. waiting_for_name - ожидание ввода имени
    2. waiting_for_age - ожидание ввода возраста
    3. waiting_for_gender - ожидание выбора пола
    4. waiting_for_city - ожидание ввода города
    5. waiting_for_bio - ожидание ввода описания (био)
    6. waiting_for_photo - ожидание загрузки фото
    7. waiting_for_video_note - ожидание загрузки кружка (video note)
    """
    
    waiting_for_name = State()
    """Ожидание ввода имени пользователя"""
    
    waiting_for_age = State()
    """Ожидание ввода возраста"""
    
    waiting_for_gender = State()
    """Ожидание выбора пола"""
    
    waiting_for_city = State()
    """Ожидание ввода города"""
    
    waiting_for_bio = State()
    """Ожидание ввода описания (био)"""
    
    waiting_for_photo = State()
    """Ожидание загрузки фото"""
    
    waiting_for_video_note = State()
    """Ожидание загрузки кружка (video note) для модерации"""
