from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class MessengerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messenger'
    label = 'messenger'

    def ready(self):
        from . import registry_app  # ⬅️ Важно: импортируем, чтобы выполнить код с @decorator
        # Импорт задач — всегда нужен, т.к. @shared_task должны быть доступны
        from . import tasks  # noqa: F401
        logger.info("Модуль messenger.tasks загружен")

        # Проверка: включена ли синхронизация?
        from django.conf import settings
        if not getattr(settings, 'ENABLE_MESSENGER', False):
            logger.info("Синхронизация с messenger отключена (ENABLE_MESSENGER=False). Пропуск регистрации задач.")
            return

        # Только если синхронизация включена — регистрируем расписание
        #if getattr(settings, 'ENABLE_MESSENGER', True):
            #self._configure_celery_beat()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from django.apps import apps


        # Регистрация разрешений отложена до готовности базы данных
        from django.core.signals import request_started
        from django.dispatch import receiver

        @receiver(request_started)
        def create_permissions_on_request(**kwargs):
            content_type = ContentType.objects.get_or_create(app_label='messenger', model='membermessenger')[0]
            Permission.objects.get_or_create(
                codename='can_access_messenger',
                name='Может получать доступ к мессенджеру',
                content_type=content_type,
            )
            logger.info("Разрешения для приложения messenger зарегистрированы.")