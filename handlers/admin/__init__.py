"""
Роутер для обработчиков администратора.
"""
from aiogram import Router

from handlers.admin.admin_commands import router as admin_commands_router
from handlers.admin.admin_users import router as admin_users_router
from handlers.admin.ai_moderation import router as ai_moderation_router

# Создание основного роутера для администраторов
admin_router = Router()

# Подключение подроутеров
admin_router.include_router(admin_commands_router)
admin_router.include_router(admin_users_router)
admin_router.include_router(ai_moderation_router)