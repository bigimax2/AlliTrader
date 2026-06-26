"""
WSGI config for Nice3 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Динамическое определение имени проекта из переменной окружения или по умолчанию
project_name = os.environ.get('PROJECT_NAME', 'Main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{project_name}.settings')

application = get_wsgi_application()
