"""
Кастомный shared_task, который привязывает задачи к правильному app.
Используйте это вместо 'from celery import shared_task'
"""

from celery import shared_task as base_shared_task
import os
import sys
from functools import wraps


def get_celery_app():
    """
    Получает правильный app для текущего проекта.
    Ищет по PROJECT_NAME или по стеку вызовов.
    """
    app = None
    
    # 1. Пробуем получить PROJECT_NAME из переменных окружения
    project_name = os.environ.get('PROJECT_NAME')
    if project_name:
        try:
            app_module = __import__(f"{project_name}.celery", fromlist=['app'])
            app = getattr(app_module, 'app', None)
            if app:
                return app
        except (ImportError, AttributeError) as e:
            print(f"[shared_task] Ошибка импорта {project_name}.celery: {e}")
    
    # 2. Пробуем Main.celery
    try:
        app_module = __import__(f"{project_name}.celery", fromlist=['app'])
        app = getattr(app_module, 'app', None)
        if app:
            return app
    except (ImportError, AttributeError) as e:
        print(f"[shared_task] Ошибка импорта Main.celery: {e}")
    
    # 3. Пробуем определить проект из стека вызовов
    try:
        # Ищем в стеке вызовов, какой модуль вызвал shared_task
        frame = sys._getframe(2)  # Пропускаем shared_task и decorator
        module_name = frame.f_globals.get('__name__', '')
        
        # Извлекаем имя проекта из module_name (например, 'momo2.groupmanagement.tasks' -> 'momo2')
        parts = module_name.split('.')
        if len(parts) >= 2:
            project_name = parts[0]  # Например, 'momo2'
            try:
                app_module = __import__(f"{project_name}.celery", fromlist=['app'])
                app = getattr(app_module, 'app', None)
                if app:
                    return app
            except (ImportError, AttributeError):
                pass
    except (ValueError, AttributeError):
        pass
    
    return app


def shared_task(*args, **kwargs):
    """Shared task, который привязывает задачи к правильному app."""
    app = get_celery_app()
    
    def decorator(func):
        if app is not None:
            # Привязываем задачу к app
            @wraps(func)
            def task_wrapper(*f_args, **f_kwargs):
                return app.task(*args, **kwargs)(func)(*f_args, **f_kwargs)
            return task_wrapper
        else:
            # Используем стандартный shared_task
            @wraps(func)
            def task_wrapper(*f_args, **f_kwargs):
                return base_shared_task(*args, **kwargs)(func)(*f_args, **f_kwargs)
            return task_wrapper
    
    # Если вызван без скобок (@shared_task instead of @shared_task())
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])
    
    return decorator
