"""
from config.celery_schedule import register_periodic_task
from celery.schedules import crontab

register_periodic_task(
    name='assign-states-every-hour',
    task='authenticated.tasks.assign_states_task',
    schedule=crontab(minute='*/5'),

)
"""