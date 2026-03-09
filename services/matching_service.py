"""
Сервис для алгоритма показа анкет (Tinder-подобный).
Содержит логику выдачи анкет с учетом boost, match_rate, активности и случайности.
"""
from typing import Optional, List
from datetime import datetime

from database.models.profile import Profile
from database.models.user import User
from database.models.like import ProfileView
from database.repositories.profile_repo import ProfileRepository
from database.repositories.boost_repo import BoostRepository
from database.repositories.like_repo import LikeRepository
from database.repositories.match_repo import MatchRepository
from database.repositories.settings_repo import SettingsRepository
from utils.randomizer import random_score
from core.constants import BOOST_FREQUENCY_DEFAULT
from core.cache import (
    get_cached_candidates, set_cached_candidates,
    get_cached_setting, set_cached_setting,
    get_cached_boost, set_cached_boost,
    invalidate_user_cache
)


class MatchingService:
    """Сервис для алгоритма показа анкет."""
    
    @staticmethod
    def get_candidates(user_id: int, min_age: int, max_age: int) -> List[Profile]:
        """
        Получает 100 кандидатов для показа пользователю.
        Исключает: себя, просмотренные, лайкнутые, забаненных, неподтвержденных.
        Использует кэширование для оптимизации (TTL 30 секунд).
        
        Args:
            user_id: ID пользователя
            min_age: Минимальный возраст для поиска
            max_age: Максимальный возраст для поиска
            
        Returns:
            Список профилей-кандидатов (до 100 штук)
        """
        # Проверяем кэш
        cached = get_cached_candidates(user_id, min_age, max_age)
        if cached is not None:
            return cached
        
        # Получаем кандидатов из БД
        candidates = ProfileRepository.get_candidates_for_user(
            user_id=user_id,
            min_age=min_age,
            max_age=max_age,
            limit=100
        )
        
        # Кэшируем результат на 30 секунд
        set_cached_candidates(user_id, min_age, max_age, candidates, ttl=30)
        
        return candidates
    
    @staticmethod
    def calculate_score(profile: Profile) -> float:
        """
        Рассчитывает рейтинг анкеты для алгоритма выдачи.
        
        Формула: score = boost * 50 + match_rate * 30 + activity_score * 10 + random(0, 5)
        
        Компоненты:
        - boost: сумма активных бустов пользователя (0=обычный, 1=реферальный, 3=платный)
        - match_rate: matches / likes_received (если likes_received = 0, то = 0)
        - activity_score: +10 если активен (< 3 дня), -10 если неактивен (>= 3 дня)
        - random(0, 5): случайное значение для непредсказуемости
        
        Args:
            profile: Объект Profile для расчета рейтинга
            
        Returns:
            Рейтинг анкеты (score)
        """
        user_id = profile.user_id
        
        # 1. Boost компонент (boost * 50)
        boost_value = BoostRepository.get_total_boost_value(user_id)
        boost_score = boost_value * 50
        
        # 2. Match rate компонент (match_rate * 30)
        matches_count = MatchRepository.count_user_matches(user_id)
        likes_received = LikeRepository.count_likes_received(user_id)
        
        if likes_received > 0:
            match_rate = matches_count / likes_received
        else:
            match_rate = 0.0
        
        match_rate_score = match_rate * 30
        
        # 3. Activity score компонент (activity_score * 10)
        # Получаем пользователя для проверки last_active
        try:
            user = User.get_by_id(user_id)
            if user.last_active:
                days_since_active = (datetime.now() - user.last_active).days
                if days_since_active < 3:
                    activity_score = 1.0  # Активен
                else:
                    activity_score = -1.0  # Неактивен
            else:
                # Если last_active не установлен, считаем неактивным
                activity_score = -1.0
        except User.DoesNotExist:
            activity_score = -1.0
        
        activity_score_value = activity_score * 10
        
        # 4. Random компонент (random(0, 5))
        random_value = random_score(0, 5)
        
        # Итоговый score
        total_score = boost_score + match_rate_score + activity_score_value + random_value
        
        return total_score
    
    @staticmethod
    def get_next_profile(user_id: int, min_age: int, max_age: int) -> Optional[Profile]:
        """
        Основной метод выдачи анкеты пользователю.
        Получает кандидатов, рассчитывает score для каждого, сортирует и возвращает лучшего.
        
        Алгоритм:
        1. Получение boost_frequency из Settings
        2. Подсчет просмотренных профилей пользователя
        3. Проверка, нужно ли показать буст-анкету (каждые N анкет)
        4. Получение 100 кандидатов через get_candidates()
        5. Если нужно показать буст - фильтрация кандидатов с boost > 0
        6. Если кандидатов нет - возврат None
        7. Для каждого кандидата расчет score через calculate_score()
        8. Сортировка по score (по убыванию)
        9. Возврат профиля с наивысшим score
        
        Args:
            user_id: ID пользователя
            min_age: Минимальный возраст для поиска
            max_age: Максимальный возраст для поиска
            
        Returns:
            Profile с наивысшим score или None если кандидатов нет
        """
        # 1. Получение boost_frequency из Settings
        boost_frequency = SettingsRepository.get_int(
            'boost_frequency',
            default=BOOST_FREQUENCY_DEFAULT
        )
        
        # 2. Подсчет просмотренных профилей пользователя
        profiles_viewed_count = ProfileView.select().where(
            ProfileView.viewer_id == user_id
        ).count()
        
        # 3. Проверка, нужно ли показать буст-анкету (каждые N анкет)
        # Если profiles_viewed_count == 0, это первая анкета, не показываем буст
        # Если profiles_viewed_count > 0 и (profiles_viewed_count % boost_frequency == 0), показываем буст
        should_show_boost = (
            profiles_viewed_count > 0 and 
            profiles_viewed_count % boost_frequency == 0
        )
        
        # 4. Получение кандидатов
        candidates = MatchingService.get_candidates(user_id, min_age, max_age)
        
        # 5. Если нужно показать буст - фильтрация кандидатов с boost > 0
        if should_show_boost:
            boosted_candidates = []
            for profile in candidates:
                boost_value = BoostRepository.get_total_boost_value(profile.user_id)
                if boost_value > 0:
                    boosted_candidates.append(profile)
            
            # Если есть буст-кандидаты, используем их
            if boosted_candidates:
                candidates = boosted_candidates
        
        # 6. Если кандидатов нет - возврат None
        if not candidates:
            return None
        
        # 7. Расчет score для каждого кандидата
        candidates_with_scores = []
        for profile in candidates:
            score = MatchingService.calculate_score(profile)
            candidates_with_scores.append((profile, score))
        
        # 8. Сортировка по score (по убыванию)
        candidates_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 9. Возврат профиля с наивысшим score
        best_profile, _ = candidates_with_scores[0]
        return best_profile
