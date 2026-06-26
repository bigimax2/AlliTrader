"""
Celery app для eveonline.
Этот файл нужен для импорта app в core/app_task.py.
"""

from celery import Celery

app = Celery('eveonline')

# Используем общие настройки из Main.celery
app.config_from_object('Main.celery', namespace='CELERY')

# Автодискавер задач
app.autodiscover_tasks()
