"""
Утилита для генерации тестовых анкет через OpenAI API.
Создает 30 тестовых профилей с разнообразными данными.
"""
import logging
import random
import json
import asyncio
from typing import Optional, Dict, List
from datetime import datetime

from openai import AsyncOpenAI

from config import config
from database.repositories.user_repo import UserRepository
from database.repositories.profile_repo import ProfileRepository
from database.models.user import User

logger = logging.getLogger(__name__)

# Валидные значения пола
VALID_GENDERS = ["Мужской", "Женский", "Другой"]

# Список популярных городов России для генерации
RUSSIAN_CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград", "Краснодар",
    "Саратов", "Тюмень", "Тольятти", "Ижевск", "Барнаул", "Ульяновск",
    "Иркутск", "Хабаровск", "Ярославль", "Владивосток", "Махачкала",
    "Томск", "Оренбург", "Кемерово"
]

class TestProfileGenerator:
    """Генератор тестовых профилей через OpenAI API."""
    
    def __init__(self, bot=None):
        """
        Инициализация генератора.
        
        Args:
            bot: Экземпляр бота Telegram (опционально, будет получен из loader если не указан)
        """
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.openai_client = None
        self.bot = bot
        
        # Инициализация OpenAI клиента
        if config.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("OpenAI клиент инициализирован для генерации тестовых профилей")
        else:
            logger.warning("OPENAI_API_KEY не установлен. Генерация будет использовать случайные данные.")
    
    def is_openai_available(self) -> bool:
        """Проверяет доступность OpenAI API."""
        return self.openai_client is not None
    
    async def generate_profile_data(self) -> Dict[str, any]:
        """
        Генерирует данные для одного профиля через OpenAI или случайно.
        
        Returns:
            Словарь с данными профиля: name, age, gender, city, bio
        """
        if self.is_openai_available():
            try:
                return await self._generate_with_openai()
            except Exception as e:
                logger.warning(f"Ошибка при генерации через OpenAI: {e}. Используем случайные данные.")
                return self._generate_random_data()
        else:
            return self._generate_random_data()
    
    async def _generate_with_openai(self) -> Dict[str, any]:
        """
        Генерирует данные профиля через OpenAI GPT.
        
        Returns:
            Словарь с данными профиля
        """
        # IMPORTANT: All prompts for OpenAI must be in English for better API performance
        prompt = (
            "Generate a realistic dating app profile. "
            "Return the answer ONLY in JSON format without any additional text:\n"
            "{\n"
            '  "name": "Russian name in Cyrillic script (first name only, no surname, e.g., Анна, Александр, Мария)",\n'
            '  "age": number from 18 to 35,\n'
            '  "gender": "Мужской" or "Женский" or "Другой",\n'
            '  "city": "City name in Russia",\n'
            '  "bio": "Brief profile description in 2-3 sentences in Russian language. '
            'Describe interests, hobbies, what the person is looking for in relationships. Be realistic and diverse."\n'
            "}\n\n"
            "IMPORTANT DIVERSITY REQUIREMENTS:\n"
            "1. NAME: Use diverse RUSSIAN names only. The name must be in Russian/Cyrillic script. "
            "Avoid only popular names (Анна, Александр, Мария, Дмитрий). "
            "Include less common but realistic Russian names (e.g., Арсений, Елизавета, Тимофей, Вероника, "
            "Глеб, Милана, Родион, Арина, Данила, Кира, Игнат, Алиса, Марк, София, Лев, Амелия, "
            "Алексей, Екатерина, Максим, Дарья, Иван, Полина, Никита, Виктория, Артем, Анастасия, etc.). "
            "NEVER use English names like Elizabeth, Veronica, Alice, Mark, Sophia, Lev, Amelia - only Russian names in Cyrillic!\n"
            "2. AGE: Distribute age evenly from 18 to 35 years. Don't concentrate on one range. "
            "Use different values: 18-22, 23-27, 28-32, 33-35.\n"
            "3. DESCRIPTION (bio): Create unique descriptions with different styles and interests. Variations:\n"
            "   - Different writing styles (formal, informal, friendly, with humor)\n"
            "   - Different interests (sports, art, travel, science, music, cooking, technology, nature, books, movies, etc.)\n"
            "   - Different wording and sentence structure\n"
            "   - Different relationship goals (serious relationships, friendship, shared interests, communication)\n"
            "4. CITY: Choose different cities from Russia. Don't limit to only Moscow and St. Petersburg. "
            "Use cities from different regions: Novosibirsk, Yekaterinburg, Kazan, Nizhny Novgorod, "
            "Chelyabinsk, Samara, Omsk, Rostov-on-Don, Ufa, Krasnoyarsk, Voronezh, Perm, Volgograd, "
            "Krasnodar, Saratov, Tyumen, Izhevsk, Barnaul, Ulyanovsk, Irkutsk, Khabarovsk, Yaroslavl, "
            "Vladivostok, Tomsk, Orenburg, Kemerovo, and others.\n\n"
            "Important: return ONLY valid JSON, without markdown formatting, without additional comments."
        )
        
        response = await self.openai_client.chat.completions.create(
            model=config.AI_MODEL or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helper for generating test data. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.9,  # Больше разнообразия
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Удаляем markdown разметку если есть
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Парсим JSON
        try:
            data = json.loads(response_text)
            
            # Валидация и нормализация данных
            name = str(data.get("name", "Тестовый")).strip()
            if not name:
                name = "Тестовый"
            
            age = int(data.get("age", random.randint(18, 35)))
            if age < 18 or age > 35:
                age = random.randint(18, 35)
            
            gender = str(data.get("gender", random.choice(VALID_GENDERS))).strip()
            if gender not in VALID_GENDERS:
                gender = random.choice(VALID_GENDERS)
            
            city = str(data.get("city", random.choice(RUSSIAN_CITIES))).strip()
            if not city:
                city = random.choice(RUSSIAN_CITIES)
            
            bio = str(data.get("bio", "")).strip()
            if not bio:
                bio = self._generate_random_bio(gender)
            
            return {
                "name": name,
                "age": age,
                "gender": gender,
                "city": city,
                "bio": bio
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Ошибка парсинга ответа OpenAI: {e}. Ответ: {response_text[:200]}")
            return self._generate_random_data()
    
    def _generate_random_data(self) -> Dict[str, any]:
        """
        Генерирует случайные данные профиля без OpenAI.
        
        Returns:
            Словарь с данными профиля
        """
        # Случайные имена
        male_names = [
            "Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей",
            "Артем", "Илья", "Кирилл", "Михаил", "Никита", "Матвей",
            "Роман", "Егор", "Арсений", "Иван", "Денис", "Евгений"
        ]
        female_names = [
            "Анна", "Мария", "Елена", "Ольга", "Татьяна", "Наталья",
            "Ирина", "Светлана", "Екатерина", "Юлия", "Анастасия", "Дарья",
            "Виктория", "Полина", "София", "Александра", "Валерия", "Ксения"
        ]
        other_names = ["Алекс", "Саша", "Крис", "Джей", "Тейлор"]
        
        gender = random.choice(VALID_GENDERS)
        if gender == "Мужской":
            name = random.choice(male_names)
        elif gender == "Женский":
            name = random.choice(female_names)
        else:
            name = random.choice(other_names)
        
        age = random.randint(18, 35)
        city = random.choice(RUSSIAN_CITIES)
        bio = self._generate_random_bio(gender)
        
        return {
            "name": name,
            "age": age,
            "gender": gender,
            "city": city,
            "bio": bio
        }
    
    def _generate_random_bio(self, gender: str) -> str:
        """Генерирует случайное описание профиля."""
        hobbies = [
            "люблю путешествовать", "увлекаюсь фотографией", "занимаюсь спортом",
            "читаю книги", "смотрю фильмы", "играю на гитаре", "готовлю",
            "занимаюсь йогой", "хожу в походы", "коллекционирую марки",
            "играю в видеоигры", "занимаюсь танцами", "изучаю языки"
        ]
        
        looking_for = [
            "ищу серьезные отношения", "хочу найти друзей", "ищу спутника жизни",
            "хочу познакомиться с интересными людьми", "ищу единомышленников",
            "хочу найти человека для совместного времяпрепровождения"
        ]
        
        hobby = random.choice(hobbies)
        looking = random.choice(looking_for)
        
        bio_templates = [
            f"Привет! {random.choice(['Меня зовут', 'Я'])} {random.choice(['активный', 'творческий', 'открытый', 'дружелюбный'])} человек. "
            f"Я {hobby}. {looking.capitalize()}.",
            
            f"Люблю жизнь и все что в ней интересного. {hobby.capitalize()}. "
            f"{looking.capitalize()}. Давай знакомиться!",
            
            f"Ищу интересных людей для общения. {hobby.capitalize()}. "
            f"{looking.capitalize()}. Открыт{'а' if gender == 'Женский' else ''} к новым знакомствам!"
        ]
        
        return random.choice(bio_templates)
    
    async def generate_test_profiles(self, count: int = 30) -> Dict[str, any]:
        """
        Генерирует указанное количество тестовых профилей.
        
        Args:
            count: Количество профилей для генерации (по умолчанию 30)
            
        Returns:
            Словарь с результатами:
            {
                'success': bool,
                'created': int,
                'errors': List[str],
                'profiles': List[Dict]
            }
        """
        logger.info(f"Начало генерации {count} тестовых профилей...")
        
        import time
        generation_start_time = time.time()
        
        results = {
            'success': True,
            'created': 0,
            'errors': [],
            'profiles': []
        }
        
        # Убеждаемся, что БД подключена
        from core.database import get_database
        db = get_database()
        if db.is_closed():
            db.connect(reuse_if_open=True)
        
        # Генерируем уникальные telegram_id для тестовых профилей
        # Используем отрицательные числа для тестовых профилей
        existing_test_ids = set()
        existing_users = User.select().where(User.role == "test")
        for user in existing_users:
            existing_test_ids.add(abs(user.telegram_id))
        
        # Начинаем с -1000000 и идем вниз
        base_telegram_id = -1000000
        
        for i in range(count):
            try:
                # Генерируем уникальный telegram_id
                telegram_id = base_telegram_id - i
                while telegram_id in existing_test_ids:
                    telegram_id -= 1
                existing_test_ids.add(abs(telegram_id))
                
                # Генерируем данные профиля
                profile_data = await self.generate_profile_data()
                
                # Создаем пользователя с role="test"
                user = self.user_repo.create(
                    telegram_id=telegram_id,
                    username=None,
                    is_banned=False,
                    is_verified=True,  # Тестовые профили сразу верифицированы
                    is_active=True,
                    role="test",
                    last_active=datetime.now()
                )
                
                # Создаем профиль
                profile = self.profile_repo.create(
                    user_id=user.id,
                    name=profile_data["name"],
                    age=profile_data["age"],
                    gender=profile_data["gender"],
                    city=profile_data["city"],
                    bio=profile_data["bio"]
                )
                
                results['created'] += 1
                results['profiles'].append({
                    'user_id': user.id,
                    'telegram_id': user.telegram_id,
                    'name': profile.name,
                    'age': profile.age,
                    'gender': profile.gender,
                    'city': profile.city
                })
                
                logger.info(
                    f"[{i+1}/{count}] ✅ Создан тестовый профиль: {profile.name}, {profile.age} лет, "
                    f"{profile.city}, {profile.gender}"
                )
                
            except Exception as e:
                error_msg = f"Ошибка при создании профиля {i+1}/{count}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                results['success'] = False
        
        # Подсчитываем финальную статистику
        total_time = time.time() - generation_start_time
        
        # Логируем статистику
        logger.info("=" * 80)
        logger.info("📊 СТАТИСТИКА ГЕНЕРАЦИИ ТЕСТОВЫХ ПРОФИЛЕЙ")
        logger.info("=" * 80)
        logger.info(f"⏱️  Общее время генерации: {total_time:.2f} секунд ({total_time/60:.2f} минут)")
        logger.info(f"👥 Создано профилей: {results['created']} из {count}")
        logger.info(f"❌ Ошибок при создании: {len(results['errors'])}")
        logger.info("=" * 80)
        
        return results
    
    @staticmethod
    def has_test_profiles() -> bool:
        """
        Проверяет, нужно ли генерировать тестовые профили.
        
        Проверяет два условия:
        1. Флаг в Settings - если установлен, значит тестовые профили уже были созданы
           (даже если потом удалены, не нужно создавать повторно)
        2. Наличие тестовых пользователей в БД - если они есть, не нужно генерировать снова
        
        Returns:
            True если тестовые профили уже существуют или были созданы ранее, False если нужно создать
        """
        try:
            # Убеждаемся, что БД подключена
            from core.database import get_database
            from database.repositories.settings_repo import SettingsRepository
            
            db = get_database()
            if db.is_closed():
                db.connect(reuse_if_open=True)
            
            # Проверяем флаг в Settings - если установлен, значит уже были созданы
            # (даже если потом удалены, не нужно создавать повторно)
            test_profiles_initialized = SettingsRepository.get_bool(
                "test_profiles_initialized", 
                default=False
            )
            
            if test_profiles_initialized:
                logger.debug("Флаг test_profiles_initialized установлен - тестовые профили уже были созданы")
                return True
            
            # Проверяем наличие тестовых пользователей в БД
            # Если они есть, значит еще не удаляли и не нужно генерировать снова
            count = User.select().where(User.role == "test").count()
            if count > 0:
                logger.debug(f"Найдено {count} тестовых пользователей в БД - не нужно генерировать повторно")
                return True
            
            # Если флаг не установлен и пользователей нет - нужно создать
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке тестовых профилей: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_test_profiles_count() -> int:
        """
        Получает количество тестовых профилей в базе данных.
        
        Returns:
            Количество тестовых профилей
        """
        try:
            # Убеждаемся, что БД подключена
            from core.database import get_database
            db = get_database()
            if db.is_closed():
                db.connect(reuse_if_open=True)
            
            return User.select().where(User.role == "test").count()
        except Exception as e:
            logger.error(f"Ошибка при подсчете тестовых профилей: {e}", exc_info=True)
            return 0


# Глобальный экземпляр генератора
_generator: Optional[TestProfileGenerator] = None


def get_test_profile_generator(bot=None) -> TestProfileGenerator:
    """
    Получает глобальный экземпляр генератора тестовых профилей.
    
    Args:
        bot: Экземпляр бота Telegram (опционально)
    
    Returns:
        TestProfileGenerator: Экземпляр генератора
    """
    global _generator
    
    if _generator is None:
        _generator = TestProfileGenerator(bot=bot)
    elif bot is not None and _generator.bot is None:
        # Обновляем бот, если он был передан и ранее не был установлен
        _generator.bot = bot
    
    return _generator


async def generate_test_profiles(count: int = 30, bot=None) -> Dict[str, any]:
    """
    Удобная функция для генерации тестовых профилей.
    
    Args:
        count: Количество профилей для генерации (по умолчанию 30)
        bot: Экземпляр бота Telegram (опционально, будет получен автоматически если не указан)
        
    Returns:
        Словарь с результатами генерации
    """
    generator = get_test_profile_generator(bot=bot)
    return await generator.generate_test_profiles(count)


def has_test_profiles() -> bool:
    """
    Проверяет наличие тестовых профилей в базе данных.
    
    Returns:
        True если есть тестовые профили, False в противном случае
    """
    return TestProfileGenerator.has_test_profiles()


def get_test_profiles_count() -> int:
    """
    Получает количество тестовых профилей в базе данных.
    
    Returns:
        Количество тестовых профилей
    """
    return TestProfileGenerator.get_test_profiles_count()
