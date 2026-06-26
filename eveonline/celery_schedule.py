"""
Расписание задач для eveonline app.
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "esi-cleanup-callbackredirect": {
        "task": "eveonline.tasks.cleanup_callbackredirect",
        "schedule": crontab(minute=0, hour=0),  # Каждую ночь
    },
    "esi-cleanup-token-subset": {
        "task": "eveonline.tasks.cleanup_token_subset",
        "schedule": crontab(minute=30, hour=0),
    },
    "update-eve-entities-hourly": {
        "task": "eveonline.tasks.update_eve_entities",
        "schedule": crontab(minute=0),  # Каждый час
    },
    "check-corp-roles-daily": {
        "task": "eveonline.tasks.check_corp_roles",
        "schedule": crontab(minute=0, hour=6),  # 6:00
    },
}
