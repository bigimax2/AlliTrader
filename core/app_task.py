"""
Декоратор app_task - привязывает задачи к конкретному app автоматически.

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

# Список модулей, которые не являются Django apps
NON_APP_MODULES = ['config', 'core']


def get_app_by_module(module_name=None):
    """
    Получает Celery app для указанного модуля (app).
    Ищет по пути модуля или имени проекта.
    """
    if module_name is None:
        # Получаем модуль вызывающего кода
        frame = sys._getframe(2)  # Пропускаем app_task decorator и wrapper
        module_name = frame.f_globals.get('__name__', '')
    
    # Извлекаем имя app из module_name (например, 'authenticated.tasks' -> 'authenticated')
    parts = module_name.split('.')
    
    if len(parts) >= 2:
        # Берём предпоследнюю часть как имя app
        app_name = parts[-2]  # Например, 'authenticated' из 'authenticated.tasks'
        
        # Проверяем, не является ли это non-app модулем
        if app_name in NON_APP_MODULES:
            # Для config и core используем Main.celery
            app_name = os.environ.get('PROJECT_NAME', 'Main')
    else:
        # Если модуль не в app, используем PROJECT_NAME
        app_name = os.environ.get('PROJECT_NAME', 'Main')
    
    # Пытаемся импортировать app
    try:
        # Сначала пробуем импортировать как app (например, 'authenticated')
        app_module = __import__(f"{app_name}.celery", fromlist=['app'])
        return getattr(app_module, 'app', None)
    except (ImportError, AttributeError):
        pass
    
    # Если не удалось, пробуем Main.celery
    try:
        app_module = __import__("Main.celery", fromlist=['app'])
        return getattr(app_module, 'app', None)
    except (ImportError, AttributeError):
        pass
    
    return None


def app_task(bind=False, **kwargs):
    """
    Декоратор для задач Celery, который автоматически привязывает задачу к правильному app.
    
    Работает как celery.shared_task, но привязывает задачи к правильному app.
    
    Args:
        bind: Если True, задача будет привязана к self (как @shared_task(bind=True))
        **kwargs: Дополнительные аргументы для app.task()
    
    Returns:
        Декоратор задачи.
    """
    # Если вызван без скобок (@app_task instead of @app_task())
    if callable(bind):
        func = bind
        bind = False
        return _app_task_decorator(func, False, **kwargs)
    
    def decorator(func):
        return _app_task_decorator(func, bind, **kwargs)
    
    return decorator


def _app_task_decorator(func, bind=False, **kwargs):
    """Внутренняя функция для декорирования задачи."""
    try:
        # Получаем имя модуля из стека вызовов
        frame = sys._getframe(1)
        module_name = frame.f_globals.get('__name__', '')
    except (ValueError, AttributeError):
        module_name = ''
    
    # Определяем app_name
    if module_name and module_name != '__main__':
        parts = module_name.split('.')
        if len(parts) >= 2:
            app_name = parts[-2]
            if app_name in NON_APP_MODULES:
                app_name = os.environ.get('PROJECT_NAME', 'Main')
        else:
            app_name = os.environ.get('PROJECT_NAME', 'Main')
    else:
        app_name = os.environ.get('PROJECT_NAME', 'Main')
    
    # Получаем app
    app = get_app_by_module(module_name)
    
    # Если app не найден, используем стандартный shared_task
    if app is None:
        from celery import shared_task as base_shared_task
        return base_shared_task(bind=bind, **kwargs)(func)
    
    # Привязываем задачу к app
    return app.task(bind=bind, **kwargs)(func)
