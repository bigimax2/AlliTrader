"""
Менеджмент команда для регистрации задач ВСЕХ разворачиваемых проектов в Redis.

Использование:
    python manage.py register_all_projects_tasks <manager_directory>
    
Где <manager_directory> - путь к директори�� менеджера, где разворачиваются экземпляры Nice3

Пример:
    python manage.py register_all_projects_tasks C:/Users/mark2/PycharmProjects/Manager
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


def get_project_celery_schedule(project_path):
    """
    Импортирует CELERY_BEAT_SCHEDULE из указанного проекта.
    Возвращает None, если проект не найден или не содержит расписания.
    """
    project_name = project_path.name
    
    try:
        # Пробуем импортировать из config.celery_schedule проекта
        module_path = f"{project_name}.config.celery_schedule"
        sys.path.insert(0, str(project_path))
        module = __import__(module_path, fromlist=['CELERY_BEAT_SCHEDULE'])
        return getattr(module, 'CELERY_BEAT_SCHEDULE', None), project_name
    except (ImportError, AttributeError) as e:
        pass
    finally:
        if str(project_path) in sys.path:
            sys.path.remove(str(project_path))

    try:
        # Пробуем импортировать напрямую из celery_schedule проекта
        module_path = f"{project_name}.celery_schedule"
        sys.path.insert(0, str(project_path))
        module = __import__(module_path, fromlist=['CELERY_BEAT_SCHEDULE'])
        return getattr(module, 'CELERY_BEAT_SCHEDULE', None), project_name
    except (ImportError, AttributeError) as e:
        pass
    finally:
        if str(project_path) in sys.path:
            sys.path.remove(str(project_path))

    return None, None


def find_all_nice3_instances(manager_dir):
    """
    Ищет все развернутые экземпляры Nice3 в директории менеджера.
    Возвращает список путей к найденным проектам.
    """
    manager_path = Path(manager_dir)
    if not manager_path.exists():
        print(f"❌ Директория менеджера не найдена: {manager_dir}")
        return []
    
    instances = []
    
    for item in manager_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Проверяем, есть ли в директории manage.py (признак проекта Django)
            if (item / 'manage.py').exists():
                # Дополнительно проверяем наличие celery_schedule.py
                config_file = item / 'config' / 'celery_schedule.py'
                simple_file = item / 'celery_schedule.py'
                
                if config_file.exists() or simple_file.exists():
                    instances.append(item)
                    print(f"  ✅ Найден проект: {item.name}")
    
    return instances


def register_tasks_for_project(project_path, redis_client, force=False):
    """Регистрирует задачи проекта в Redis."""
    
    project_name = project_path.name
    
    # Ищем расписание для проекта
    beat_schedule, project_name = get_project_celery_schedule(project_path)
    
    if not beat_schedule:
        print(f"  ⚠️  Не найдено расписание для '{project_name}'")
        return False
    
    print(f"  📁 Проект: {project_name}")
    print(f"  📋 Задач в расписании: {len(beat_schedule)}")
    
    # Получаем текущий список задач
    all_tasks_key = "celery_schedule:all_tasks"
    tasks_json = redis_client.get(all_tasks_key)
    
    if tasks_json:
        task_names = set(json.loads(tasks_json))
    else:
        task_names = set()
    
    registered_count = 0
    
    for task_name, task_config in beat_schedule.items():
        redis_key = f"celery_schedule:{project_name}:{task_name}"
        
        # Проверяем, существует ли уже задача
        if not force and redis_client.exists(redis_key):
            print(f"    ⏭️  Задача '{task_name}' уже существует (используйте --force для перезаписи)")
            continue
        
        # Подготавливаем данные для Redis
        # Добавляем префикс project_name к имени задачи для уникальности
        schedule_data = {
            "task": f"{project_name}.{task_config.get('task')}",
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
        task_names.add(redis_key)
        registered_count += 1
        
        print(f"    ✅ Задача '{task_name}' из '{project_name}' зарегистрирована")
    
    # Обновляем список всех задач
    redis_client.set(all_tasks_key, json.dumps(list(task_names)))
    
    print(f"  🎉 Зарегистрировано {registered_count} задач")
    return True


class Command(BaseCommand):
    help = "Регистрирует задачи всех разворачиваемых проектов в Redis (для менеджера)"

    def add_arguments(self, parser):
        parser.add_argument(
            'manager_directory',
            nargs='?',
            type=str,
            help='Путь к директории менеджера с развернутыми экземплярами Nice3'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезаписывает существующие задачи'
        )

    def handle(self, *args, **options):
        """Обработка команды."""
        manager_dir = options['manager_directory']
        force = options['force']
        
        if not manager_dir:
            self.stdout.write(self.style.WARNING('⚠️  Укажите путь к директории менеджера'))
            self.stdout.write('Пример: python manage.py register_all_projects_tasks C:/Users/mark2/PycharmProjects/Manager')
            return
        
        self.stdout.write(self.style.SUCCESS('🚀 Регистрация задач всех проектов в Redis'))
        self.stdout.write("=" * 60)
        self.stdout.write(f"📍 Директория менеджера: {manager_dir}")
        self.stdout.write("=" * 60)
        
        # Подключение к Redis
        try:
            redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            self.stdout.write(self.style.SUCCESS('✅ Подключение к Redis успешно'))
        except redis.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка подключения к Redis: {e}'))
            return
        
        # Ищем все экземпляры Nice3
        instances = find_all_nice3_instances(manager_dir)
        
        if not instances:
            self.stdout.write(self.style.WARNING('❌ Не найдено развернутых экземпляров Nice3'))
            return
        
        self.stdout.write(f"\n📋 Найдено экземпляров: {len(instances)}\n")
        
        total_registered = 0
        successful_instances = 0
        
        for instance_path in instances:
            self.stdout.write(f"\n📦 Обработка: {instance_path.name}")
            self.stdout.write("-" * 40)
            
            if register_tasks_for_project(instance_path, redis_client, force):
                successful_instances += 1
                # Получаем количество задач для этого проекта
                try:
                    beat_schedule, _ = get_project_celery_schedule(instance_path)
                    total_registered += len(beat_schedule) if beat_schedule else 0
                except:
                    pass
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠️  Регистрация для {instance_path.name} не удалась"))
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"🎉 Регистрация завершена!"))
        self.stdout.write(f"   Успешно обработано экземпляров: {successful_instances} из {len(instances)}")
        self.stdout.write(f"   Всего задач зарегистрировано: {total_registered}")
        self.stdout.write("=" * 60)
