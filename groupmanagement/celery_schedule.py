"""
Расписание задач для groupmanagement app.
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "check-nicegroup-user-states": {
        "task": 'groupmanagement.tasks.check_nicegroup_user_states',
        "schedule": crontab(minute='*/1'),
    },
}
