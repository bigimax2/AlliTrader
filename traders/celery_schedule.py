from celery.schedules import crontab

CELERY_BEAT_SCHEDULE={
    'get_prices': {
        'task':'traders.tasks.get_prices',
        'schedule': crontab(minute="*/30"),
    }
}