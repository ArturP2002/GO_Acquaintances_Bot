"""
Роутер для обработчиков модерации.
"""
from aiogram import Router

from handlers.moderation.moderation_queue import router as moderation_queue_router

# Создание основного роутера для модерации
moderation_router = Router()

# Подключение подроутеров
moderation_router.include_router(moderation_queue_router)
