"""
API endpoints для управления настройками.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from admin_panel.mini_app.backend.dependencies import get_current_admin, require_admin
from admin_panel.mini_app.backend.schemas import (
    SettingResponse, SettingUpdate,
    TestProfilesCountResponse, DeleteTestProfilesResponse
)
from database.models.user import User
from database.repositories.settings_repo import SettingsRepository
from core.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

# Отдельный роутер для тестовых анкет (будет зарегистрирован с префиксом /api/test-profiles)
test_profiles_router = APIRouter()


@router.get("/", response_model=list[SettingResponse])
async def get_all_settings(
    admin: User = Depends(get_current_admin)
):
    """
    Получение всех настроек с дефолтными значениями.
    Возвращает важные настройки бота, создавая их с дефолтными значениями, если их нет.
    
    Доступ: все администраторы
    """
    try:
        # Убеждаемся, что БД подключена
        from core.database import get_database
        db = get_database()
        if db.is_closed():
            db.connect(reuse_if_open=True)
        
        from core.constants import (
            MAX_LIKES_PER_DAY_DEFAULT,
            BOOST_FREQUENCY_DEFAULT,
            MIN_AGE_DEFAULT
        )
        from config import config
        
        # Определяем важные настройки с дефолтными значениями
        important_settings = {
            "max_likes_per_day": {
                "value": str(MAX_LIKES_PER_DAY_DEFAULT),
                "description": "Лимит лайков в день",
                "icon": "❤️",
                "min": 1,
                "max": 1000
            },
            "boost_frequency": {
                "value": str(BOOST_FREQUENCY_DEFAULT),
                "description": "Частота показа буста (каждые N анкет)",
                "icon": "🚀",
                "min": 1,
                "max": 100
            },
            "min_age": {
                "value": str(getattr(config, 'MIN_AGE', MIN_AGE_DEFAULT)),
                "description": "Минимальный возраст для регистрации",
                "icon": "🔞",
                "min": 16,
                "max": 100
            },
            "referral_bonus": {
                "value": str(getattr(config, 'REFERRAL_BONUS', 10)),
                "description": "Бонус за реферала (boost_value)",
                "icon": "🎁",
                "min": 1,
                "max": 100
            }
        }
        
        # Получаем существующие настройки
        existing_settings = SettingsRepository.get_all()
        existing_keys = {s.key for s in existing_settings}
        
        # Создаем настройки, которых нет в БД
        result = []
        for key, setting_info in important_settings.items():
            if key in existing_keys:
                # Используем существующую настройку
                setting = next(s for s in existing_settings if s.key == key)
                result.append(SettingResponse.model_validate(setting))
            else:
                # Создаем новую настройку с дефолтным значением
                setting = SettingsRepository.set(key, setting_info["value"])
                result.append(SettingResponse.model_validate(setting))
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении настроек: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении настроек"
        )


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    admin: User = Depends(get_current_admin)
):
    """
    Получение настройки по ключу.
    
    Доступ: все администраторы
    """
    from database.models.settings import Settings
    
    try:
        setting = Settings.get(Settings.key == key)
        return SettingResponse.model_validate(setting)
    except Settings.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Настройка '{key}' не найдена"
        )


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_update: SettingUpdate,
    admin: User = Depends(require_admin)
):
    """
    Обновление настройки с валидацией.
    
    Доступ: admin и выше
    """
    try:
        # Валидация числовых значений для важных настроек
        validation_rules = {
            "max_likes_per_day": {"min": 1, "max": 1000},
            "boost_frequency": {"min": 1, "max": 100},
            "min_age": {"min": 16, "max": 100},
            "referral_bonus": {"min": 1, "max": 100}
        }
        
        if key in validation_rules:
            try:
                value = int(setting_update.value)
                rules = validation_rules[key]
                if value < rules["min"] or value > rules["max"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Значение должно быть от {rules['min']} до {rules['max']}"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Значение должно быть числом"
                )
        
        setting = SettingsRepository.set(key, setting_update.value)
        
        logger.info(
            f"Администратор {admin.id} обновил настройку '{key}': "
            f"новое значение = {setting_update.value}"
        )
        
        return SettingResponse.model_validate(setting)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении настройки '{key}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении настройки '{key}'"
        )


@router.delete("/{key}")
async def delete_setting(
    key: str,
    admin: User = Depends(require_admin)
):
    """
    Удаление настройки.
    
    Доступ: admin и выше
    """
    success = SettingsRepository.delete(key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Настройка '{key}' не найдена"
        )
    
    logger.info(f"Администратор {admin.id} удалил настройку '{key}'")
    
    return {"message": f"Настройка '{key}' удалена"}


@test_profiles_router.get("/count", response_model=TestProfilesCountResponse)
async def get_test_profiles_count(
    admin: User = Depends(require_admin)
):
    """
    Получение количества тестовых анкет.
    
    Доступ: admin и выше
    """
    try:
        # Убеждаемся, что БД подключена
        db = get_database()
        if db.is_closed():
            db.connect(reuse_if_open=True)
        
        # Подсчитываем пользователей с role="test"
        count = User.select().where(User.role == "test").count()
        
        logger.debug(f"Администратор {admin.id} запросил количество тестовых анкет: {count}")
        
        return TestProfilesCountResponse(count=count)
    except Exception as e:
        logger.error(f"Ошибка при получении количества тестовых анкет: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении количества тестовых анкет"
        )


@test_profiles_router.delete("/", response_model=DeleteTestProfilesResponse)
async def delete_test_profiles(
    admin: User = Depends(require_admin)
):
    """
    Удаление всех тестовых анкет.
    
    Удаляет всех пользователей с role="test" и их связанные данные (профили, медиа и т.д.)
    благодаря CASCADE удалению.
    
    Доступ: admin и выше
    """
    try:
        # Убеждаемся, что БД подключена
        db = get_database()
        if db.is_closed():
            db.connect(reuse_if_open=True)
        
        # Получаем всех пользователей с role="test"
        test_users = User.select().where(User.role == "test")
        count = test_users.count()
        
        if count == 0:
            logger.info(f"Администратор {admin.id} попытался удалить тестовые анкеты, но их нет")
            return DeleteTestProfilesResponse(
                message="Тестовые анкеты не найдены",
                deleted_count=0
            )
        
        # Используем транзакцию для безопасного удаления
        with db.atomic():
            # Удаляем всех тестовых пользователей
            # CASCADE удаление автоматически удалит связанные профили, медиа и другие данные
            deleted_count = User.delete().where(User.role == "test").execute()
        
        logger.info(
            f"Администратор {admin.id} удалил {deleted_count} тестовых анкет"
        )
        
        return DeleteTestProfilesResponse(
            message=f"Успешно удалено {deleted_count} тестовых анкет",
            deleted_count=deleted_count
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении тестовых анкет: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении тестовых анкет"
        )
