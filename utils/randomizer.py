"""
Утилиты для генерации случайных значений.
Используется в алгоритме показа анкет для непредсказуемости.
"""
import random


def random_score(min_value: float = 0, max_value: float = 5) -> float:
    """
    Генерирует случайное значение для добавления к score анкеты.
    Используется для непредсказуемости ленты.
    
    Args:
        min_value: Минимальное значение (по умолчанию 0)
        max_value: Максимальное значение (по умолчанию 5)
        
    Returns:
        Случайное значение в диапазоне [min_value, max_value]
    """
    return random.uniform(min_value, max_value)
