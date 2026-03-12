"""
Фоновая задача для автоматической отправки рекламных кампаний.
Выполняется каждую минуту для проверки и отправки рекламы по расписанию.
"""
import logging
from datetime import datetime

from loader import get_bot
from services.advertisement_service import AdvertisementService

logger = logging.getLogger(__name__)


async def send_advertisements_task():
    """
    Фоновая задача для автоматической отправки рекламных кампаний.
    Выполняется каждую минуту (или каждые 5 минут для оптимизации).
    
    Логика:
    1. Получает все активные рекламные кампании
    2. Для каждой кампании проверяет:
       - Наступило ли время отправки (сравнивает текущее время с send_time)
       - Не отправлялась ли уже сегодня (сравнивает дату last_sent_at с текущей датой)
    3. Если условия выполнены - отправляет рекламу только owner'ам через сервис
    4. Сервис автоматически обновляет last_sent_at после успешной отправки
    """
    try:
        logger.debug("Запуск задачи отправки рекламных кампаний...")
        
        # Получаем бота и создаем сервис
        bot = get_bot()
        advertisement_service = AdvertisementService(bot)
        
        # Получаем текущее время
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # Получаем активные кампании для текущего времени
        campaigns_to_send = advertisement_service.get_active_campaigns_for_time(
            current_hour,
            current_minute
        )
        
        if not campaigns_to_send:
            logger.debug(
                f"Нет активных кампаний для отправки в {current_hour:02d}:{current_minute:02d}"
            )
            return
        
        logger.info(
            f"Найдено {len(campaigns_to_send)} активных кампаний "
            f"для отправки в {current_hour:02d}:{current_minute:02d}"
        )
        
        # Проверяем каждую кампанию и отправляем, если нужно
        sent_count = 0
        skipped_count = 0
        
        for campaign in campaigns_to_send:
            try:
                # Проверяем, не отправлялась ли уже сегодня
                if campaign.last_sent_at is not None:
                    last_sent_date = campaign.last_sent_at.date()
                    current_date = now.date()
                    
                    if last_sent_date == current_date:
                        logger.debug(
                            f"Кампания {campaign.id} уже была отправлена сегодня "
                            f"({campaign.last_sent_at}). Пропускаем."
                        )
                        skipped_count += 1
                        continue
                
                # Отправляем рекламу всем активным пользователям
                logger.info(
                    f"Отправка рекламной кампании {campaign.id} "
                    f"(время: {campaign.send_time}, текст: {bool(campaign.text)})"
                )
                
                sent_users_count = await advertisement_service.send_advertisement_to_all_users(
                    campaign.id
                )
                
                if sent_users_count > 0:
                    sent_count += 1
                    logger.info(
                        f"Кампания {campaign.id} успешно отправлена "
                        f"{sent_users_count} пользователям"
                    )
                else:
                    logger.warning(
                        f"Кампания {campaign.id} не была отправлена "
                        "(возможно, нет активных пользователей или произошла ошибка)"
                    )
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(
                    f"Ошибка при обработке кампании {campaign.id}: {e}",
                    exc_info=True
                )
                skipped_count += 1
                continue
        
        logger.info(
            f"Задача отправки рекламных кампаний завершена. "
            f"Отправлено: {sent_count}, пропущено: {skipped_count}"
        )
        
    except Exception as e:
        logger.error(
            f"Ошибка при выполнении задачи отправки рекламных кампаний: {e}",
            exc_info=True
        )
