"""
Декоратор app_task - привязывает задачи к Main.celery.

Используйте это вместо 'from celery import shared_task'.

Пример:
    from core.app_task import app_task
    
    @app_task()
    def my_task():
        pass
    
    @app_task(bind=True, max_retries=3)
    def my_task(self):
        pass
"""

import os
import sys
from functools import wraps


def app_task(bind=False, **kwargs):
    """
    Декоратор для задач Celery, который привязывает задачу к Main.celery.
    
    Работает как celery.shared_task, но привязывает задачи к Main.celery.
    
    Args:
        bind: Если True, задача будет привязана к self (как @shared_task(bind=True))
        **kwargs: Дополнительные аргументы для app.task()
    
    Returns:
        Декоратор задачи.
    """
    # Импортируем Main.celery
    try:
        app_module = __import__("Main.celery", fromlist=['app'])
        app = getattr(app_module, 'app', None)
    except (ImportError, AttributeError) as e:
        print(f"[app_task] Ошибка импорта Main.celery: {e}")
        app = None
    
    # Если app не найден, используем стандартный shared_task
    if app is None:
        from celery import shared_task as base_shared_task
        
        if callable(bind):
            func = bind
            bind = False
            return base_shared_task(bind=bind, **kwargs)(func)
        
        def decorator(func):
            return base_shared_task(bind=bind, **kwargs)(func)
        return decorator
    
    # Если вызван без скобок (@app_task instead of @app_task())
    if callable(bind):
        func = bind
        bind = False
        return app.task(bind=bind, **kwargs)(func)
    
    def decorator(func):
        return app.task(bind=bind, **kwargs)(func)
    
    return decorator
