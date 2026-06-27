"""
Расписание задач для groupmanagement app.
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "observer_assets":{
        "task": "trader.tasks.get_personage_assets",
        "schedule": crontab(minute="*/30"), # evry 30 minut
    }
}
