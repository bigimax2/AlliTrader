"""
⚠️ Этот файл может выполняться как в режиме менеджера (без Django), так и в Celery.
Цель: объединить расписание из всех apps и заполнить CELERY_BEAT_SCHEDULE для менеджера, но безопасно.

ВАЖНО: Имена задач здесь должны быть без префикса PROJECT_NAME, так как он будет добавлен в Main/celery.py
"""

import os

# Импортируем расписания из всех apps
from authenticated.celery_schedule import CELERY_BEAT_SCHEDULE as AUTH_SCHEDULE
from groupmanagement.celery_schedule import CELERY_BEAT_SCHEDULE as GROUPMAN_SCHEDULE
from eveonline.celery_schedule import CELERY_BEAT_SCHEDULE as EVEONLINE_SCHEDULE
from core.celery_schedule import CELERY_BEAT_SCHEDULE as CORE_SCHEDULE
from observer_assets_single.celery_schedule import CELERY_BEAT_SCHEDULE as OBSERVER_ASSETS_SINGLE_SCHEDULE
from traders.celery_schedule import CELERY_BEAT_SCHEDULE as TRADERS_SCHEDULE

# Объединяем все расписания в одно с уникальными именами для каждого проекта
CELERY_BEAT_SCHEDULE = {}

# Получаем имя проекта из переменных окружения
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'Main')

# Добавляем расписание из each app с префиксом PROJECT_NAME
for name, task_config in AUTH_SCHEDULE.items():
    # Формируем полное имя задачи с префиксом PROJECT_NAME
    # Важно: name уже содержит уникальное имя, просто добавляем префикс
    full_name = f"{PROJECT_NAME}.{name}"
    CELERY_BEAT_SCHEDULE[full_name] = {
        "task": task_config["task"],
        "schedule": task_config["schedule"],
    }


for name, task_config in GROUPMAN_SCHEDULE.items():
    full_name = f"{PROJECT_NAME}.{name}"
    CELERY_BEAT_SCHEDULE[full_name] = {
        "task": task_config["task"],
        "schedule": task_config["schedule"],
    }

for name, task_config in EVEONLINE_SCHEDULE.items():
    full_name = f"{PROJECT_NAME}.{name}"
    CELERY_BEAT_SCHEDULE[full_name] = {
        "task": task_config["task"],
        "schedule": task_config["schedule"],
    }

for name, task_config in CORE_SCHEDULE.items():
    full_name = f"{PROJECT_NAME}.{name}"
    CELERY_BEAT_SCHEDULE[full_name] = {
        "task": task_config["task"],
        "schedule": task_config["schedule"],
    }

for name, task_config in OBSERVER_ASSETS_SINGLE_SCHEDULE.items():
    full_name = f"{PROJECT_NAME}.{name}"
    CELERY_BEAT_SCHEDULE[full_name] = {
        "task": task_config["task"],
        "schedule": task_config["schedule"],
    }

for name, task_config in TRADERS_SCHEDULE.items():
 full_name = f"{PROJECT_NAME}.{name}"
 CELERY_BEAT_SCHEDULE[full_name] = {
     "task": task_config["task"],
     "schedule": task_config["schedule"],
 }