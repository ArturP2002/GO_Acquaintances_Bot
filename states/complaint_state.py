"""
FSM состояния для процесса создания жалобы на пользователя.
Используется для сбора информации о жалобе.
"""
from aiogram.fsm.state import State, StatesGroup


class ComplaintState(StatesGroup):
    """
    Группа состояний для создания жалобы.
    
    Последовательность состояний:
    1. waiting_for_reason - ожидание выбора причины жалобы
    2. waiting_for_description - ожидание ввода описания жалобы
    """
    
    waiting_for_reason = State()
    """Ожидание выбора причины жалобы (18+, Наркотики, Фейк, Оскорбления, Другое)"""
    
    waiting_for_description = State()
    """Ожидание ввода описания жалобы (опционально)"""
