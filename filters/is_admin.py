"""
Фильтр для проверки прав администратора.
Проверяет, является ли пользователь администратором (owner/admin/moderator/support).
"""
import logging
from typing import Any

from aiogram.filters.base import Filter
from aiogram.types import TelegramObject

from core.constants import AdminRole

logger = logging.getLogger(__name__)

# Иерархия ролей (чем выше число, тем больше прав)
ROLE_HIERARCHY = {
    AdminRole.OWNER: 4,
    AdminRole.ADMIN: 3,
    AdminRole.MODERATOR: 2,
    AdminRole.SUPPORT: 1
}


class IsAdmin(Filter):
    """
    Фильтр для проверки прав администратора.
    
    Проверяет наличие записи в таблице AdminUsers для пользователя.
    Поддерживает проверку конкретной роли (owner/admin/moderator/support).
    Если роль не указана, проверяет наличие любой роли администратора.
    Если указана роль, проверяет что пользователь имеет эту роль или выше (иерархия).
    """
    
    def __init__(self, role: str | None = None, exact: bool = False):
        """
        Инициализация фильтра.
        
        Args:
            role: Конкретная роль для проверки (owner/admin/moderator/support).
                  Если None, проверяет наличие любой роли администратора.
                  Если указана, проверяет что пользователь имеет эту роль или выше (если exact=False).
            exact: Если True, проверяет точное совпадение роли. Если False, проверяет иерархию.
        """
        self.role = role
        self.exact = exact
    
    async def __call__(
        self,
        obj: TelegramObject,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Проверка прав администратора.
        
        Args:
            obj: Событие Telegram
            data: Контекстные данные (должен содержать "user")
            
        Returns:
            True если пользователь является администратором с указанной ролью,
            False в противном случае
        """
        # Получаем telegram_id из объекта события
        telegram_id = None
        if hasattr(obj, 'from_user') and obj.from_user:
            telegram_id = obj.from_user.id
        elif hasattr(obj, 'message') and obj.message and obj.message.from_user:
            telegram_id = obj.message.from_user.id
        
        if telegram_id is None:
            logger.debug("Не удалось получить telegram_id из события")
            return False
        
        # Получаем пользователя из контекста (должен быть добавлен UserContextMiddleware)
        user = None
        if data is not None:
            user = data.get("user")
        
        # Если пользователь не загружен из контекста, пытаемся загрузить из БД
        if user is None:
            try:
                from database.models.user import User
                # Получаем базу данных из контекста или напрямую из loader
                database = None
                if data is not None:
                    database = data.get("database")
                
                # Если база данных не найдена в контексте, пытаемся получить её напрямую
                if database is None:
                    try:
                        from loader import get_database
                        database = get_database()
                    except (ImportError, RuntimeError):
                        logger.warning("Контекстные данные не предоставлены для проверки прав администратора")
                        # Пытаемся использовать глобальную базу данных из core.database
                        try:
                            from core.database import get_database_instance
                            database = get_database_instance()
                        except ImportError:
                            pass
                
                if database is not None:
                    try:
                        # Убеждаемся, что база данных подключена
                        if database.is_closed():
                            database.connect()
                        user = User.get(User.telegram_id == telegram_id)
                        logger.debug(f"Пользователь {telegram_id} загружен из БД для проверки прав администратора")
                    except User.DoesNotExist:
                        logger.debug(f"Пользователь {telegram_id} не найден в БД")
                        return False
                else:
                    logger.warning("База данных не найдена для проверки прав администратора")
                    return False
            except ImportError:
                logger.debug("Модель User не найдена, проверка прав администратора невозможна")
                return False
            except Exception as e:
                logger.error(f"Ошибка при загрузке пользователя для проверки прав администратора: {e}", exc_info=True)
                return False
        
        # Пытаемся импортировать модель AdminUser
        try:
            from database.models.settings import AdminUser
        except ImportError:
            # Модель AdminUser еще не создана - логируем и возвращаем False
            logger.debug("Модель AdminUser не найдена, проверка прав администратора невозможна")
            return False
        
        try:
            # Получаем ID пользователя из модели User
            user_id = getattr(user, "id", None)
            if user_id is None:
                logger.debug("Не удалось получить ID пользователя для проверки прав администратора")
                return False
            
            # Проверяем наличие записи в AdminUsers
            admin_user = AdminUser.select().where(
                AdminUser.user_id == user_id
            ).first()
            
            if admin_user is None:
                logger.debug(f"Пользователь {user_id} не является администратором")
                return False
            
            # Если роль не указана, проверяем наличие любой роли администратора
            if self.role is None:
                logger.debug(f"Пользователь {user_id} является администратором (роль: {admin_user.role})")
                return True
            
            # Проверяем конкретную роль
            if self.exact:
                # Точное совпадение роли
                if admin_user.role == self.role:
                    logger.debug(f"Пользователь {user_id} имеет роль {self.role}")
                    return True
                else:
                    logger.debug(f"Пользователь {user_id} не имеет роли {self.role} (текущая роль: {admin_user.role})")
                    return False
            else:
                # Проверка иерархии ролей (пользователь должен иметь требуемую роль или выше)
                user_role_level = ROLE_HIERARCHY.get(admin_user.role, 0)
                required_role_level = ROLE_HIERARCHY.get(self.role, 0)
                
                if user_role_level >= required_role_level:
                    logger.debug(f"Пользователь {user_id} имеет роль {admin_user.role} (>= {self.role})")
                    return True
                else:
                    logger.debug(f"Пользователь {user_id} имеет роль {admin_user.role} (< {self.role})")
                    return False
                
        except Exception as e:
            logger.error(f"Ошибка при проверке прав администратора: {e}", exc_info=True)
            # В случае ошибки возвращаем False для безопасности
            return False
