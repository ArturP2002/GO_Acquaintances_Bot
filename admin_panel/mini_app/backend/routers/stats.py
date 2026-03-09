"""
API endpoints для получения статистики.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from admin_panel.mini_app.backend.dependencies import get_current_admin
from admin_panel.mini_app.backend.schemas import StatsResponse
from database.models.user import User
from database.repositories.complaint_repo import ComplaintRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=StatsResponse)
async def get_stats(
    admin: User = Depends(get_current_admin)
):
    """
    Получение общей статистики для дашборда.
    
    Возвращает:
    - totalUsers: общее количество пользователей
    - totalProfiles: общее количество профилей
    - totalLikes: общее количество лайков
    - totalMatches: общее количество мэтчей
    - bannedUsers: количество забаненных пользователей
    - verifiedUsers: количество верифицированных пользователей
    - pendingComplaints: количество ожидающих обработки жалоб
    
    Доступ: все администраторы
    """
    try:
        # Убеждаемся, что БД подключена
        from core.database import get_database
        db = get_database()
        if db.is_closed():
            db.connect(reuse_if_open=True)
        
        from database.models.profile import Profile
        from database.models.like import Like
        from database.models.match import Match
        
        # Подсчет общего количества пользователей
        total_users = User.select().count()
        
        # Подсчет общего количества профилей
        total_profiles = Profile.select().count()
        
        # Подсчет общего количества лайков
        total_likes = Like.select().count()
        
        # Подсчет общего количества мэтчей
        total_matches = Match.select().count()
        
        # Подсчет забаненных пользователей
        banned_users = User.select().where(User.is_banned == True).count()
        
        # Подсчет верифицированных пользователей
        verified_users = User.select().where(User.is_verified == True).count()
        
        # Подсчет ожидающих жалоб
        pending_complaints = ComplaintRepository.get_pending()
        pending_count = len(pending_complaints)
        
        return StatsResponse(
            totalUsers=total_users,
            totalProfiles=total_profiles,
            totalLikes=total_likes,
            totalMatches=total_matches,
            bannedUsers=banned_users,
            verifiedUsers=verified_users,
            pendingComplaints=pending_count
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики"
        )
