"""
Фоновые задачи для бота знакомств.
Все задачи выполняются через APScheduler.
"""
from tasks.reset_likes import reset_likes_task
from tasks.send_referral_reminders import send_referral_reminders_task
from tasks.cleanup_moderation_queue import cleanup_moderation_queue_task
from tasks.profile_boost_rotation import profile_boost_rotation_task

__all__ = [
    "reset_likes_task",
    "send_referral_reminders_task",
    "cleanup_moderation_queue_task",
    "profile_boost_rotation_task",
    "register_all_tasks",
]


def register_all_tasks(scheduler):
    """
    Регистрирует все фоновые задачи в планировщике.
    
    Args:
        scheduler: Экземпляр AsyncIOScheduler
        
    Задачи:
        - reset_likes_task: Ежедневно в 00:00 UTC - очистка старых данных лайков
        - send_referral_reminders_task: Каждые 2 часа - напоминания о рефералах
        - cleanup_moderation_queue_task: Ежедневно в 01:00 UTC - очистка очереди модерации
        - profile_boost_rotation_task: Ежедневно в 02:00 UTC - очистка истекших бустов
    """
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    
    # Очистка старых данных лайков - ежедневно в 00:00 UTC
    scheduler.add_job(
        reset_likes_task,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="reset_likes",
        name="Очистка старых данных лайков",
        replace_existing=True
    )
    
    # Напоминания о рефералах - каждые 2 часа
    scheduler.add_job(
        send_referral_reminders_task,
        trigger=IntervalTrigger(hours=2),
        id="send_referral_reminders",
        name="Отправка напоминаний о рефералах",
        replace_existing=True
    )
    
    # Очистка очереди модерации - ежедневно в 01:00 UTC
    scheduler.add_job(
        cleanup_moderation_queue_task,
        trigger=CronTrigger(hour=1, minute=0, timezone="UTC"),
        id="cleanup_moderation_queue",
        name="Очистка очереди модерации",
        replace_existing=True
    )
    
    # Очистка истекших бустов - ежедневно в 02:00 UTC
    scheduler.add_job(
        profile_boost_rotation_task,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="profile_boost_rotation",
        name="Очистка истекших бустов",
        replace_existing=True
    )
