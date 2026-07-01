import os.path
from django.apps import AppConfig


class EveonlineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eveonline'
    
    # Аннотация для IDE, чтобы избежать предупреждений о несуществующем атрибуте
    esi = None

    def ready(self):
        # Импорт esi.openapi_clients может вызывать ошибки при старте
        # поэтому обернем его в try-except
        try:
            from esi.openapi_clients import ESIClientProvider
            base_dir = os.path.dirname(os.path.abspath(__file__))
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
        except (ImportError, ModuleNotFoundError) as e:
            print(f"[WARNING] Не удалось загрузить ESIClientProvider: {e}")
            print("[WARNING] Периодические задачи могут не работать корректно")