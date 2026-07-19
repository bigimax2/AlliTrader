from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ObserverAssetsSingleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'observer_assets_single'
    label ='observer_assets_single'

    def ready(self):
        from . import registry_app  # ⬅️ Важно: импортируем, чтобы выполнить код с @decorator
        # Импорт задач — всегда нужен, т.к. @shared_task должны быть доступны
        from . import tasks  # noqa: F401
        logger.info("Модуль observer_assets_single.tasks загружен")

        # Импорт сигналов для обновления количества ассетов в TypeSearchResult
        from . import signals  # noqa: F401
        logger.info("Модуль observer_assets_single.signals загружен")

        # Проверка: включена ли синхронизация?
        from django.conf import settings
        if not getattr(settings, 'ENABLE_OBSERVER_ASSETS_SINGLE', False):
            logger.info("Синхронизация с messenger отключена (ENABLE_OBSERVER_ASSETS_SINGLE=False). Пропуск регистрации задач.")
            return

        # Только если синхронизация включена — регистрируем расписание
        #if getattr(settings, 'ENABLE_TRADER', True):
            #self._configure_celery_beat()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from django.apps import apps


        # Регистрация разрешений отложена до готовности базы данных
        # from django.core.signals import request_started
        # from django.dispatch import receiver
        # Дополнительная инициализация при необходимости

