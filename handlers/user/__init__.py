"""
Роутер для обработчиков пользователей.
"""
from aiogram import Router

from handlers.user.start import router as start_router
from handlers.user.registration import router as registration_router
from handlers.user.browse_profiles import router as browse_profiles_router
from handlers.user.likes import router as likes_router
from handlers.user.matches import router as matches_router
from handlers.user.referrals import router as referrals_router
from handlers.user.complaints import router as complaints_router

# Создание основного роутера для пользователей
user_router = Router()

# Подключение подроутеров
# referrals_router должен быть подключен, но не обрабатывает /start напрямую
# (функция process_referral_link_async вызывается из start.py)
user_router.include_router(referrals_router)
user_router.include_router(start_router)
user_router.include_router(registration_router)
user_router.include_router(browse_profiles_router)
user_router.include_router(likes_router)
user_router.include_router(matches_router)
user_router.include_router(complaints_router)