import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

class TradersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traders'
    label = 'traders'

    def ready(self):
        from . import registry_app  # ⬅️ Важно: импортируем, чтобы выполнить код с @decorator
        # Импорт задач — всегда нужен, т.к. @shared_task должны быть доступны
        from . import tasks  # noqa: F401
        logger.info("Модуль traders.tasks загружен")

        # Проверка: включена ли синхронизация?
        from django.conf import settings
        if not getattr(settings, 'ENABLE_TRADERS', False):
            logger.info("Синхронизация с messenger отключена (ENABLE_TRADERS=False). Пропуск регистрации задач.")
            return


        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from django.apps import apps
