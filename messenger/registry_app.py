from core.registry import app_registry
from django.conf import settings
import os
import sys


@app_registry.decorator('messenger')
def messenger_sidebar_config():
    # Проверяем, включено ли приложение в настройках
    if not getattr(settings, 'ENABLE_MESSENGER', True):
        return None

    # Регистрируем приложение только в основном процессе при использовании runserver
    is_runserver = 'runserver' in sys.argv
    is_main_process = os.environ.get('RUN_MAIN') == 'true'
    if is_runserver and not is_main_process:
        return None

    return {
        'name': 'Nice_messenger',
        'icon': '💬',
        'url': 'messenger:render_messenger_template',
    }