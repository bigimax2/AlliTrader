"""
⚠️ Этот файл может выполняться как в режиме менеджера (без Django), так и в Celery.
Цель: объединить расписание из всех apps и заполнить CELERY_BEAT_SCHEDULE для менеджера, но безопасно.
"""

import os

# Получаем имя проекта из переменных окружения
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'Main')

# Импортируем расписания из всех apps
from authenticated.celery_schedule import CELERY_BEAT_SCHEDULE as AUTH_SCHEDULE
from groupmanagement.celery_schedule import CELERY_BEAT_SCHEDULE as GROUPMAN_SCHEDULE
from eveonline.celery_schedule import CELERY_BEAT_SCHEDULE as EVEONLINE_SCHEDULE
from core.celery_schedule import CELERY_BEAT_SCHEDULE as CORE_SCHEDULE

# Объединяем все расписания в одно с уникальными именами для каждого проекта
CELERY_BEAT_SCHEDULE = {}

# Добавляем расписание из each app с префиксом PROJECT_NAME
for name, task_config in AUTH_SCHEDULE.items():
    # Формируем полное имя задачи с префиксом PROJECT_NAME
    full_task_name = f"{PROJECT_NAME}.authenticated.tasks.assign_states_task" if name == "assign-states-every-hour" else f"{PROJECT_NAME}.{name}"
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
