from django.apps import AppConfig


class GroupmanagementConfig(AppConfig):
    default_auto_file = 'django.db.models.BigAutoField'
    name = 'groupmanagement'

    def ready(self):
        import groupmanagement.signals  # Регистрируем сигналы
