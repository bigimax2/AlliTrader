import os
import sys
import inspect
from pathlib import Path
from celery import Celery

# Добавляем корневую директорию проекта в PYTHONPATH
# Это необходимо для того, чтобы Celery мог найти модули проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Определяем имя проекта
# Приоритет: 1) PROJECT_NAME из env, 2) автоматическое определение
PROJECT_NAME = os.environ.get('PROJECT_NAME')

if not PROJECT_NAME:
    # Автоматическое определение имени проекта
    # Ищем директорию, содержащую manage.py
    try:
        # Ищем родительскую директорию, содержащую manage.py
        current_dir = Path(__file__).resolve().parent
        while current_dir.parent != current_dir:  # Пока не дошли до корня
            if (current_dir / 'manage.py').exists():
                # Нашли директорию с manage.py
                manage_dir = current_dir
                # Имя проекта - это имя директории (или из INSTALLED_APPS)
                # Пытаемся найти в INSTALLED_APPS модуль, который не системный
                try:
                    # Пробуем импортировать настройки из разных возможных модулей
                    possible_modules = ['Main.settings', 'config.settings', 'settings']
                    for mod in possible_modules:
                        try:
                            __import__(mod)
                            # Извлекаем имя проекта из модуля
                            project_name = mod.split('.')[0]
                            if project_name and project_name not in ['django', 'config', 'settings']:
                                PROJECT_NAME = project_name
                                break
                        except (ImportError, AttributeError):
                            continue
                    if not PROJECT_NAME:
                        PROJECT_NAME = 'Main'
                except Exception:
                    PROJECT_NAME = 'Main'
                break
            current_dir = current_dir.parent
        
        if not PROJECT_NAME:
            PROJECT_NAME = 'Main'
            
    except Exception as e:
        print(f"[WARNING] Ошибка при автоматическом определении PROJECT_NAME: {e}")
        PROJECT_NAME = 'Main'

print(f"[INFO] Инициализация Celery для проекта: {PROJECT_NAME}")

# Импортируем settings напрямую, чтобы инициализировать Django
settings_module = f"{PROJECT_NAME}.settings"
try:
    __import__(settings_module)
    print(f"[INFO] Используется проект: {PROJECT_NAME}")
except ImportError as e:
    print(f"[ERROR] Не удалось импортировать {settings_module}: {e}")
    # Пытаемся найти проект, который содержит settings
    import glob
    
    print("[INFO] Попытка найти правильный модуль settings...")
    
    # Ищем все возможные settings.py файлы в проекте
    for settings_file in glob.glob('**/settings.py', recursive=True):
        parts = settings_file.split('/')
        if len(parts) >= 2:
            potential_project = parts[0]
            potential_module = f"{potential_project}.settings"
            try:
                print(f"[INFO] Пробуем модуль: {potential_module}")
                __import__(potential_module)
                PROJECT_NAME = potential_project
                print(f"[INFO] Найден правильный проект: {PROJECT_NAME}")
                break
            except (ImportError, AttributeError):
                continue
    
    if not PROJECT_NAME:
        print(f"[ERROR] Не удалось определить PROJECT_NAME")
        raise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{PROJECT_NAME}.settings")

app = Celery(PROJECT_NAME)

# Явно указываем настройки, чтобы избежать проблем с lazy loading
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Импортируем настройки из Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автодискавер задач из всех приложений
app.autodiscover_tasks()

# Импортируем и загружаем расписание задач из config.celery_schedule
try:
    from config.celery_schedule import CELERY_BEAT_SCHEDULE
    app.conf.beat_schedule.update(CELERY_BEAT_SCHEDULE)
    print(f"[INFO] Загружено задач из расписания: {len(CELERY_BEAT_SCHEDULE)}")
except ImportError as e:
    print(f"[WARNING] config.celery_schedule не найден или не может быть импортирован для {PROJECT_NAME}: {e}")
