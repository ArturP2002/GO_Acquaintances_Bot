"""
Core модули для бота знакомств.
Содержит базовые компоненты: база данных, планировщик, безопасность, константы.
"""

from core.database import (
    get_database,
    init_database,
    close_database,
    is_database_initialized,
    get_database_instance
)

from core.scheduler import (
    get_scheduler,
    init_scheduler,
    start_scheduler,
    stop_scheduler,
    is_scheduler_running,
    get_scheduler_instance
)

from core.security import (
    validate_age,
    validate_username,
    validate_telegram_id,
    sanitize_text,
    hash_data,
    verify_hmac,
    check_login_attempts,
    record_login_attempt,
    is_suspicious_activity,
    generate_secure_token,
    validate_referral_code,
    clean_login_attempts_cache
)

from core.constants import (
    AdminRole,
    ModerationStatus,
    ComplaintStatus,
    ComplaintReason,
    BoostType,
    VIDEO_NOTE_TASKS,
    ACTIVE_USER_THRESHOLD_DAYS,
    CLEANUP_PROFILE_HISTORY_DAYS,
    CLEANUP_PROFILE_VIEWS_DAYS,
    CLEANUP_MODERATION_QUEUE_DAYS,
    REFERRAL_OFFER_PROBABILITY,
    MATCHING_CANDIDATES_LIMIT,
    BOOST_MULTIPLIER,
    MATCH_RATE_MULTIPLIER,
    ACTIVITY_SCORE_MULTIPLIER,
    RANDOM_SCORE_MAX,
    MIN_AGE_DEFAULT,
    MAX_AGE_DEFAULT,
    MAX_LIKES_PER_DAY_DEFAULT,
    BOOST_FREQUENCY_DEFAULT,
    REFERRAL_BONUS_DEFAULT,
    DATABASE_PRAGMAS,
    MIN_PASSWORD_LENGTH,
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_TIME,
    THROTTLING_RATE,
    THROTTLING_BURST,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)

__all__ = [
    # Database
    'get_database',
    'init_database',
    'close_database',
    'is_database_initialized',
    'get_database_instance',
    # Scheduler
    'get_scheduler',
    'init_scheduler',
    'start_scheduler',
    'stop_scheduler',
    'is_scheduler_running',
    'get_scheduler_instance',
    # Security
    'validate_age',
    'validate_username',
    'validate_telegram_id',
    'sanitize_text',
    'hash_data',
    'verify_hmac',
    'check_login_attempts',
    'record_login_attempt',
    'is_suspicious_activity',
    'generate_secure_token',
    'validate_referral_code',
    'clean_login_attempts_cache',
    # Constants
    'AdminRole',
    'ModerationStatus',
    'ComplaintStatus',
    'ComplaintReason',
    'BoostType',
    'VIDEO_NOTE_TASKS',
    'ACTIVE_USER_THRESHOLD_DAYS',
    'CLEANUP_PROFILE_HISTORY_DAYS',
    'CLEANUP_PROFILE_VIEWS_DAYS',
    'CLEANUP_MODERATION_QUEUE_DAYS',
    'REFERRAL_OFFER_PROBABILITY',
    'MATCHING_CANDIDATES_LIMIT',
    'BOOST_MULTIPLIER',
    'MATCH_RATE_MULTIPLIER',
    'ACTIVITY_SCORE_MULTIPLIER',
    'RANDOM_SCORE_MAX',
    'MIN_AGE_DEFAULT',
    'MAX_AGE_DEFAULT',
    'MAX_LIKES_PER_DAY_DEFAULT',
    'BOOST_FREQUENCY_DEFAULT',
    'REFERRAL_BONUS_DEFAULT',
    'DATABASE_PRAGMAS',
    'MIN_PASSWORD_LENGTH',
    'MAX_LOGIN_ATTEMPTS',
    'LOGIN_LOCKOUT_TIME',
    'THROTTLING_RATE',
    'THROTTLING_BURST',
    'LOG_FORMAT',
    'LOG_DATE_FORMAT',
]
