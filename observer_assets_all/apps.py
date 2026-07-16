from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ObserverAssetsAllConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'observer_assets_all'
    label = 'observer_assets_all'
    verbose_name = 'Observer Assets All'

    def ready(self):
        from . import registry_app  # ⬅️ Важно: импортируем, чтобы выполнить код с @decorator
        # Импорт задач — всегда нужен, т.к. @shared_task должны быть доступны
        from . import tasks  # noqa: F401
        logger.info("Модуль observer_assets_all.tasks загружен")

        # Проверка: включена ли синхронизация?
        from django.conf import settings
        if not getattr(settings, 'ENABLE_OBSERVER_ASSETS_ALL', False):
            logger.info("Синхронизация с observer_assets отключена (ENABLE_OBSERVER_ASSETS_ALL=False). Пропуск регистрации задач.")
            return

        # Только если синхронизация включена — регистрируем расписание
        #if getattr(settings, 'ENABLE_OBSERVER_ASSETS', True):
            #self._configure_celery_beat()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from django.apps import apps


        # Регистрация разрешений отложена до готовности базы данных
        # from django.core.signals import request_started
        # from django.dispatch import receiver
        # Дополнительная инициализация при необходимости