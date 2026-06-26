from django.apps import AppConfig

#from config.celery_schedule import autodiscover_schedules


class AutenticatedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authenticated'

    def ready(self):
        import authenticated.signals
        #autodiscover_schedules()