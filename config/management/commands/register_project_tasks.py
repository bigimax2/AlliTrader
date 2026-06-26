"""
Менеджмент команда для регистрации задач разворачиваемого проекта в Redis.

Использование:
    python manage.py register_project_tasks <project_name>
    
Опции:
    --all               Регистрирует задачи всех проектов
    --force             Перезаписывает существующие задачи
"""

import json
import sys
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

# Добавляем путь к проекту
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Main.settings")

import django
django.setup()

import redis
from celery.schedules import crontab, timedelta


def serialize_schedule(schedule):
    """Сериализует расписание в JSON-совместимый формат."""
    if isinstance(schedule, crontab):
        return {
            "__type__": "crontab",
            "minute": schedule._orig_minute,
            "hour": schedule._orig_hour,
            "day_of_week": schedule._orig_day_of_week,
            "day_of_month": schedule._orig_day_of_month,
            "month_of_year": schedule._orig_month_of_year,
        }
    elif isinstance(schedule, timedelta):
        return {
            "__type__": "timedelta",
            "seconds": schedule.total_seconds(),
        }
    else:
        return str(schedule)


def get_project_celery_schedule(project_name):
    """
    Импортирует CELERY_BEAT_SCHEDULE из указанного проекта.
    Возвращает None, если проект не найден или не содержит расписания.
    """
    try:
        # Пробуем импортировать из config.celery_schedule проекта
        module_path = f"{project_name}.config.celery_schedule"
        module = __import__(module_path, fromlist=['CELERY_BEAT_SCHEDULE'])
        return getattr(module, 'CELERY_BEAT_SCHEDULE', None)
    except (ImportError, AttributeError):
        pass

    try:
        # Пробуем импортировать напрямую из celery_schedule проекта
        module_path = f"{project_name}.celery_schedule"
        module = __import__(module_path, fromlist=['CELERY_BEAT_SCHEDULE'])
        return getattr(module, 'CELERY_BEAT_SCHEDULE', None)
    except (ImportError, AttributeError):
        pass

    return None


def get_all_projects():
    """Возвращает список всех проектов в проекте."""
    projects = []
    
    # Ищем в корне проекта
    root_dir = BASE_DIR
    for item in root_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Проверяем, есть ли в директории manage.py или settings
            if (item / 'manage.py').exists() or (item / 'settings.py').exists():
                projects.append(item.name)
    
    return projects


def register_tasks_for_project(project_name, force=False):
    """Регистрирует задачи проекта в Redis."""
    
    # Ищем расписание для проекта
    beat_schedule = get_project_celery_schedule(project_name)
    
    if not beat_schedule:
        print(f"❌ Не найдено расписание для проекта '{project_name}'")
        return False
    
    # Подключение к Redis
    try:
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
    except redis.ConnectionError as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return False
    
    # Получаем текущий список задач
    all_tasks_key = "celery_schedule:all_tasks"
    tasks_json = redis_client.get(all_tasks_key)
    
    if tasks_json:
        task_names = set(json.loads(tasks_json))
    else:
        task_names = set()
    
    registered_count = 0
    
    for task_name, task_config in beat_schedule.items():
        redis_key = f"celery_schedule:{task_name}"
        
        # Проверяем, существует ли уже задача
        if not force and redis_client.exists(redis_key):
            print(f"⏭️  Задача '{task_name}' уже существует (используйте --force для перезаписи)")
            continue
        
        # Подготавливаем данные для Redis
        schedule_data = {
            "task": task_config.get("task"),
            "schedule": serialize_schedule(task_config.get("schedule")),
            "args": task_config.get("args", []),
            "kwargs": task_config.get("kwargs", {}),
            "options": task_config.get("options", {}),
            "enabled": task_config.get("enabled", True),
            "last_run_at": task_config.get("last_run_at", None),
        }
        
        # Удаляем None значения
        schedule_data = {k: v for k, v in schedule_data.items() if v is not None}
        
        # Сохраняем в Redis
        redis_client.set(redis_key, json.dumps(schedule_data, indent=2))
        task_names.add(task_name)
        registered_count += 1
        
        print(f"✅ Задача '{task_name}' из '{project_name}' зарегистрирована")
    
    # Обновляем список всех задач
    redis_client.set(all_tasks_key, json.dumps(list(task_names)))
    
    print(f"\n🎉 Регистрация завершена: {registered_count} новых задач")
    return True


class Command(BaseCommand):
    help = "Регистрирует задачи разворачиваемого проекта в Redis"

    def add_arguments(self, parser):
        parser.add_argument(
            'project_name',
            nargs='?',
            type=str,
            help='Имя проекта для регистрации (или все, если не указано)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Регистрирует задачи всех проектов'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезаписывает существующие задачи'
        )

    def handle(self, *args, **options):
        """Обработка команды."""
        project_name = options['project_name']
        register_all = options['all']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('🚀 Регистрация задач проекта в Redis'))
        self.stdout.write("=" * 60)
        
        if register_all:
            # Регистрируем все проекты
            projects = get_all_projects()
            
            if not projects:
                self.stdout.write(self.style.WARNING('❌ Не найдено проектов для регистрации'))
                return
            
            self.stdout.write(f"📋 Найдено проектов: {len(projects)}")
            
            success_count = 0
            for project in projects:
                self.stdout.write(f"\n📦 Работа с проектом: {project}")
                if register_tasks_for_project(project, force):
                    success_count += 1
            
            self.stdout.write(self.style.SUCCESS(f"\n🎉 Успешно зарегистрировано {success_count} из {len(projects)} проектов"))
        
        elif project_name:
            # Регистрируем конкретный проект
            if register_tasks_for_project(project_name, force):
                self.stdout.write(self.style.SUCCESS('\n✅ Регистрация завершена!'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠️  Регистрация не удалась'))
        
        else:
            self.stdout.write(self.style.WARNING('⚠️  Укажите имя проекта или используйте --all'))
            self.stdout.write('Пример: python manage.py register_project_tasks myproject')
