"""Задачи для core app."""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def clear_expired_celery_results(self):
    """Очистка устаревших результатов задач из БД."""
    try:
        from django_celery_results.models import TaskResult
        from django.utils import timezone
        from datetime import timedelta
        
        # Получаем время жизни результатов из настроек (по умолчанию 24 часа)
        from django.conf import settings
        expires = getattr(settings, 'CELERY_RESULT_EXPIRES', 86400)
        
        # Вычисляем пороговое время
        threshold = timezone.now() - timedelta(seconds=expires)
        
        # Удаляем устаревшие результаты
        deleted_count, _ = TaskResult.objects.filter(date_done__lt=threshold).delete()
        
        logger.info(f"Очищено {deleted_count} устаревших результатов задач Celery")
        
        return f"Очищено {deleted_count} результатов"
        
    except Exception as e:
        logger.error(f"Ошибка при очистке результатов Celery: {e}")
        raise
