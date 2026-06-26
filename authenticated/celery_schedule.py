"""
Расписание задач для authenticated app.
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'assign-states-every-hour': {
        "task": "authenticated.tasks.assign_states_task",
        "schedule": crontab(minute='*/5'),
    },
}
