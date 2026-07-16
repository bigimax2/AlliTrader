from core.registry import app_registry
from django.conf import settings
import os
import sys


@app_registry.decorator('observer_assets_all')
def observer_assets_config():
    # Проверяем, включено ли приложение в настройках
    if not getattr(settings, 'ENABLE_OBSERVER_ASSETS_ALL', False):
        return None

    # Регистрируем приложение только в основном процессе при использовании runserver
    is_runserver = 'runserver' in sys.argv
    is_main_process = os.environ.get('RUN_MAIN') == 'true'
    if is_runserver and not is_main_process:
        return None

    return {
        'name': 'Observer_assets_all',
        'icon': '📈',
        'url': 'observer_assets_all:assets_overview',

    }