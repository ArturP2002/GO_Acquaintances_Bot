"""
Репозиторий для работы с профилями.
Слой доступа к данным для моделей Profile и ProfileMedia.
"""
from typing import Optional, List
from datetime import datetime

from database.models.profile import Profile, ProfileMedia
from database.models.like import ProfileView, ProfileHistory
from database.models.user import User


class ProfileRepository:
    """Репозиторий для работы с профилями."""
    
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[Profile]:
        """
        Получает профиль по ID пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Profile или None если не найден
        """
        try:
            return Profile.get(Profile.user_id == user_id)
        except Profile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id(profile_id: int) -> Optional[Profile]:
        """
        Получает профиль по ID.
        
        Args:
            profile_id: ID профиля
            
        Returns:
            Profile или None если не найден
        """
        try:
            return Profile.get_by_id(profile_id)
        except Profile.DoesNotExist:
            return None
    
    @staticmethod
    def create(user_id: int, name: str, age: int, gender: str, 
               city: Optional[str] = None, bio: Optional[str] = None,
               min_age_preference: int = 18, max_age_preference: int = 100) -> Profile:
        """
        Создает новый профиль.
        
        Args:
            user_id: ID пользователя
            name: Имя пользователя
            age: Возраст
            gender: Пол
            city: Город (опционально)
            bio: Описание профиля (опционально)
            min_age_preference: Минимальный возраст для поиска
            max_age_preference: Максимальный возраст для поиска
            
        Returns:
            Созданный объект Profile
        """
        return Profile.create(
            user_id=user_id,
            name=name,
            age=age,
            gender=gender,
            city=city,
            bio=bio,
            min_age_preference=min_age_preference,
            max_age_preference=max_age_preference
        )
    
    @staticmethod
    def update(profile_id: int, **kwargs) -> bool:
        """
        Обновляет профиль.
        
        Args:
            profile_id: ID профиля
            **kwargs: Поля для обновления (name, age, gender, city, bio, min_age_preference, max_age_preference)
            
        Returns:
            True если обновление успешно, False если профиль не найден
        """
        try:
            profile = Profile.get_by_id(profile_id)
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.save()
            return True
        except Profile.DoesNotExist:
            return False
    
    @staticmethod
    def add_media(profile_id: int, photo_file_id: Optional[str] = None,
                  video_note_file_id: Optional[str] = None, is_main: bool = False) -> ProfileMedia:
        """
        Добавляет медиа к профилю (фото или кружок).
        
        Args:
            profile_id: ID профиля
            photo_file_id: File ID фото в Telegram (опционально)
            video_note_file_id: File ID кружка в Telegram (опционально)
            is_main: Является ли это главным фото
            
        Returns:
            Созданный объект ProfileMedia
        """
        return ProfileMedia.create(
            profile_id=profile_id,
            photo_file_id=photo_file_id,
            video_note_file_id=video_note_file_id,
            is_main=is_main
        )
    
    @staticmethod
    def get_main_photo(profile_id: int) -> Optional[ProfileMedia]:
        """
        Получает главное фото профиля.
        
        Args:
            profile_id: ID профиля
            
        Returns:
            ProfileMedia с главным фото или None
        """
        try:
            return ProfileMedia.get(
                (ProfileMedia.profile_id == profile_id) &
                (ProfileMedia.is_main == True) &
                (ProfileMedia.photo_file_id.is_null(False))
            )
        except ProfileMedia.DoesNotExist:
            return None
    
    @staticmethod
    def get_video_note(profile_id: int) -> Optional[ProfileMedia]:
        """
        Получает кружок (video note) профиля.
        
        Args:
            profile_id: ID профиля
            
        Returns:
            ProfileMedia с кружком или None
        """
        try:
            return ProfileMedia.get(
                (ProfileMedia.profile_id == profile_id) &
                (ProfileMedia.video_note_file_id.is_null(False))
            )
        except ProfileMedia.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_media(profile_id: int) -> List[ProfileMedia]:
        """
        Получает все медиа профиля.
        
        Args:
            profile_id: ID профиля
            
        Returns:
            Список всех медиа профиля
        """
        return list(ProfileMedia.select().where(ProfileMedia.profile_id == profile_id))
    
    @staticmethod
    def add_view(viewer_id: int, profile_id: int) -> ProfileView:
        """
        Добавляет запись о просмотре анкеты.
        Используется для исключения повторного показа анкеты.
        
        Args:
            viewer_id: ID пользователя, который просмотрел анкету
            profile_id: ID просмотренного профиля
            
        Returns:
            Созданный объект ProfileView
        """
        # Используем get_or_create для избежания дубликатов
        profile_view, created = ProfileView.get_or_create(
            viewer_id=viewer_id,
            profile_id=profile_id,
            defaults={'created_at': datetime.now()}
        )
        return profile_view
    
    @staticmethod
    def is_viewed(viewer_id: int, profile_id: int) -> bool:
        """
        Проверяет, была ли анкета уже просмотрена пользователем.
        
        Args:
            viewer_id: ID пользователя
            profile_id: ID профиля
            
        Returns:
            True если анкета уже просмотрена, False в противном случае
        """
        return ProfileView.select().where(
            (ProfileView.viewer_id == viewer_id) &
            (ProfileView.profile_id == profile_id)
        ).exists()
    
    @staticmethod
    def get_viewed_profiles(user_id: int) -> List[int]:
        """
        Получает список ID профилей, которые уже были просмотрены пользователем.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список ID просмотренных профилей
        """
        return [
            view.profile_id 
            for view in ProfileView.select().where(ProfileView.viewer_id == user_id)
        ]
    
    @staticmethod
    def get_candidates_for_user(user_id: int, min_age: int, max_age: int, 
                                limit: int = 100) -> List[Profile]:
        """
        Получает кандидатов для показа пользователю.
        Исключает: себя, просмотренные, лайкнутые, забаненных, неподтвержденных.
        Если включен фильтр по полу, показывает только противоположный пол.
        
        Args:
            user_id: ID пользователя
            min_age: Минимальный возраст
            max_age: Максимальный возраст
            limit: Максимальное количество кандидатов
            
        Returns:
            Список профилей-кандидатов
        """
        from database.models.like import Like
        from database.models.user import User
        
        # Получаем профиль пользователя для проверки фильтра по полу
        user_profile = ProfileRepository.get_by_user_id(user_id)
        
        # Подзапросы для исключения
        viewed_profiles = ProfileView.select(ProfileView.profile_id).where(
            ProfileView.viewer_id == user_id
        )
        
        liked_profiles = Like.select(Like.to_user_id).where(
            Like.from_user_id == user_id
        )
        
        # Основной запрос
        query_conditions = [
            (User.is_banned == False),
            (User.is_verified == True),
            (Profile.age >= min_age),
            (Profile.age <= max_age),
            (Profile.user_id != user_id),
            ~(Profile.id.in_(viewed_profiles)),
            ~(Profile.user_id.in_(liked_profiles))
        ]
        
        # Добавляем фильтр по противоположному полу, если включен
        if user_profile and user_profile.filter_by_opposite_gender:
            user_gender = user_profile.gender
            if user_gender == "Мужской":
                # Показываем только женский пол
                query_conditions.append(Profile.gender == "Женский")
            elif user_gender == "Женский":
                # Показываем только мужской пол
                query_conditions.append(Profile.gender == "Мужской")
            # Для "Другой" не фильтруем по полу
        
        # Объединяем все условия
        combined_condition = query_conditions[0]
        for condition in query_conditions[1:]:
            combined_condition = combined_condition & condition
        
        query = Profile.select().join(User).where(combined_condition).limit(limit)
        
        return list(query)
    
    @staticmethod
    def add_to_history(user_id: int, profile_id: int) -> ProfileHistory:
        """
        Добавляет профиль в историю просмотров с автоматическим определением позиции.
        Позиция определяется как максимальная позиция + 1 для данного пользователя.
        Также ограничивает историю до последних 10 записей.
        
        Args:
            user_id: ID пользователя
            profile_id: ID профиля для добавления в историю
            
        Returns:
            Созданный объект ProfileHistory
        """
        # Получаем максимальную позицию для пользователя
        max_position_query = ProfileHistory.select().where(
            ProfileHistory.user_id == user_id
        ).order_by(ProfileHistory.position.desc()).limit(1)
        
        if max_position_query.exists():
            max_position = max_position_query.get().position
            new_position = max_position + 1
        else:
            new_position = 0
        
        # Создаем новую запись в истории
        history_entry = ProfileHistory.create(
            user_id=user_id,
            profile_id=profile_id,
            position=new_position
        )
        
        # Ограничиваем историю до последних 10 записей
        ProfileRepository.cleanup_old_history(user_id, max_history=10)
        
        return history_entry
    
    @staticmethod
    def get_current_position(user_id: int) -> int:
        """
        Получает текущую позицию в истории для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Текущая позиция (максимальная позиция) или -1 если истории нет
        """
        max_position_query = ProfileHistory.select().where(
            ProfileHistory.user_id == user_id
        ).order_by(ProfileHistory.position.desc()).limit(1)
        
        if max_position_query.exists():
            return max_position_query.get().position
        return -1
    
    @staticmethod
    def get_previous_profile(user_id: int, current_position: int) -> Optional[Profile]:
        """
        Получает предыдущий профиль из истории (позиция - 1).
        
        Args:
            user_id: ID пользователя
            current_position: Текущая позиция в истории
            
        Returns:
            Profile предыдущей анкеты или None если это первая анкета
        """
        if current_position <= 0:
            return None
        
        previous_position = current_position - 1
        
        try:
            history_entry = ProfileHistory.get(
                (ProfileHistory.user_id == user_id) &
                (ProfileHistory.position == previous_position)
            )
            return history_entry.profile
        except ProfileHistory.DoesNotExist:
            return None
    
    @staticmethod
    def cleanup_old_history(user_id: int, max_history: int = 10) -> None:
        """
        Ограничивает историю просмотров до последних N записей.
        Удаляет старые записи, оставляя только последние max_history записей.
        
        Args:
            user_id: ID пользователя
            max_history: Максимальное количество записей в истории (по умолчанию 10)
        """
        # Получаем все записи истории для пользователя, отсортированные по позиции
        all_history = ProfileHistory.select().where(
            ProfileHistory.user_id == user_id
        ).order_by(ProfileHistory.position.desc())
        
        # Если записей больше max_history, удаляем старые
        history_list = list(all_history)
        if len(history_list) > max_history:
            # Оставляем только последние max_history записей
            to_delete = history_list[max_history:]
            for entry in to_delete:
                entry.delete_instance()