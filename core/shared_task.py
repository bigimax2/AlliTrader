"""
Кастомный shared_task, который привязывает задачи к правильному app.
Используйте это вместо 'from celery import shared_task'

После очистки celery.py файлов используется только Main.celery.
"""

from celery import shared_task as base_shared_task
import os
import sys
from functools import wraps


def get_celery_app():
    """
    Получает правильный app для текущего проекта.
    Использует только Main.celery после очистки.
    """
    app = None
    
    # Используем только Main.celery после очистки
    try:
        app_module = __import__("Main.celery", fromlist=['app'])
        app = getattr(app_module, 'app', None)
        if app:
            return app
    except (ImportError, AttributeError) as e:
        print(f"[shared_task] Ошибка импорта Main.celery: {e}")
    
    return app


def shared_task(*args, **kwargs):
    """Shared task, который привязывает задачи к Main.celery."""
    app = get_celery_app()
    
    def decorator(func):
        if app is not None:
            # Привязываем задачу к Main.celery
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
