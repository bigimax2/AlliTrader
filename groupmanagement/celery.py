"""
Celery app для проекта.

Для проекта используется единый Celery app из Main.celery.
Этот файл оставлен для обратной совместимости, но не используется.
"""

# Импортируем app из Main.celery для обратной совместимости
from Main.celery import app

__all__ = ('app',)
