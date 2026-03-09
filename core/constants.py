"""
Константы проекта для бота знакомств.
Содержит все константы, используемые в различных модулях системы.
"""

# Роли администраторов
class AdminRole:
    """Роли администраторов в системе."""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"


# Статусы модерации
class ModerationStatus:
    """Статусы задач модерации."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BANNED = "banned"


# Статусы жалоб
class ComplaintStatus:
    """Статусы жалоб."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# Причины жалоб
class ComplaintReason:
    """Причины жалоб на пользователей."""
    ADULT_CONTENT = "18+"
    DRUGS = "drugs"
    FAKE = "fake"
    HARASSMENT = "harassment"
    OTHER = "other"


# Типы бустов
class BoostType:
    """Типы бустов для анкет."""
    NORMAL = 0  # Обычный (без буста)
    REFERRAL = 1  # Реферальный буст
    PAID = 3  # Платный буст


# Задания для кружков (video notes)
VIDEO_NOTE_TASKS = [
    "Покажи 👍",
    "Покажи 👎",
    "Покажи ✌️",
    "Скажи 'привет'",
    "Помаши рукой",
    "Покажи два пальца",
    "Покажи кулак",
    "Покажи OK 👌",
]

# Настройки активности пользователей
ACTIVE_USER_THRESHOLD_DAYS = 3  # Пользователь считается активным, если заходил менее 3 дней назад

# Настройки очистки данных
CLEANUP_PROFILE_HISTORY_DAYS = 30  # Удаление истории просмотров старше 30 дней
CLEANUP_PROFILE_VIEWS_DAYS = 30  # Удаление просмотров старше 30 дней
CLEANUP_MODERATION_QUEUE_DAYS = 7  # Удаление записей модерации старше 7 дней

# Настройки реферальной системы
REFERRAL_OFFER_PROBABILITY = 0.1  # Вероятность показа предложения пригласить друга (10%)

# Настройки алгоритма матчинга
MATCHING_CANDIDATES_LIMIT = 100  # Количество кандидатов для последующей сортировки
BOOST_MULTIPLIER = 50  # Множитель для boost в формуле score
MATCH_RATE_MULTIPLIER = 30  # Множитель для match_rate в формуле score
ACTIVITY_SCORE_MULTIPLIER = 10  # Множитель для activity_score в формуле score
RANDOM_SCORE_MAX = 5  # Максимальное случайное значение для score

# Настройки возраста
MIN_AGE_DEFAULT = 16  # Минимальный возраст по умолчанию
MAX_AGE_DEFAULT = 100  # Максимальный возраст по умолчанию

# Настройки лимитов
MAX_LIKES_PER_DAY_DEFAULT = 50  # Максимальное количество лайков в день по умолчанию
BOOST_FREQUENCY_DEFAULT = 15  # Частота показа буст-анкет (каждые N анкет) по умолчанию
REFERRAL_BONUS_DEFAULT = 10  # Реферальный бонус (boost_value) по умолчанию

# Настройки базы данных
DATABASE_PRAGMAS = {
    'journal_mode': 'delete',  # Обычный режим журналирования (без WAL для лучшей синхронизации)
    'foreign_keys': 1,  # Включение внешних ключей
    'ignore_check_constraints': 0,
    'synchronous': 1,  # Безопасный режим записи
    'cache_size': -64000,  # 64MB кэша
}

# Настройки безопасности
MIN_PASSWORD_LENGTH = 8  # Минимальная длина пароля (если будет использоваться)
MAX_LOGIN_ATTEMPTS = 5  # Максимальное количество попыток входа
LOGIN_LOCKOUT_TIME = 300  # Время блокировки после превышения попыток (в секундах)

# Настройки throttling
THROTTLING_RATE = 1  # Количество запросов в секунду
THROTTLING_BURST = 3  # Максимальное количество запросов за раз

# Настройки логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
