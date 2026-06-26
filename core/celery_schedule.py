"""
Расписание задач для core app (общие задачи).
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "cleanup-sessions": {
        "task": "django.contrib.sessions.management.commands.clearsessions",
        "schedule": crontab(minute=0, hour=2),  # 2:00
    },
    "clear-expired-celery-results": {
        "task": "core.tasks.clear_expired_celery_results",
        "schedule": crontab(minute=0, hour=3),  # 3:00 (после очистки сессий)
    },
}
