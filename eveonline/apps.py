import os.path

from django.apps import AppConfig

#from config.celery_schedule import autodiscover_schedules


class EveonlineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eveonline'

    def ready(self):
        from esi.openapi_clients import ESIClientProvider
        base_dir = os.path.dirname(os.path.abspath(__file__))
        #autodiscover_schedules()
        swagger_path = os.path.join(
            base_dir,'swagger.json'
        )
        self.esi = ESIClientProvider(
            compatibility_date="2025-07-23",
            ua_appname="Nice3",
            ua_version="1.38",
            tags=["Alliance",
                  "Calendar",
                  "Character",
                  "Corporation",
                  "Mail",
                  "Universe",
                  "Assets",
                        ]
        )