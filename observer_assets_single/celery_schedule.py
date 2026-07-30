"""
Расписание задач для groupmanagement app.
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "observer_assets":{
        "task": "observer_assets_single.tasks.get_personage_assets",
        "schedule": crontab(minute="*/15"), # evry 15 minut
    },
    "check_all_alerts":{
        "task":"observer_assets_single.tasks.check_alerts",
        "schedule": crontab(minute="*/20"),
    }
}
