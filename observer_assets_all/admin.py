from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.apps import AppConfig
from observer_assets_all.apps import ObserverAssetsConfig


class ObserverAssetsAdminSite(admin.AdminSite):
    """Кастомная админ-панель для отображения приложений без моделей"""
    site_title = 'Observer Assets Administration'
    site_header = 'Observer Assets'
    index_title = 'Модули Observer Assets'
    
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        
        app_config = ObserverAssetsConfig
        
        # Проверяем, добавили ли мы уже это приложение
        for app in app_list:
            if app['app_label'] == app_config.name.lower():
                return app_list
        
        # Создаем запись для приложения без моделей
        observer_app = {
            'name': app_config.verbose_name,
            'app_label': app_config.name.lower(),
            'app_url': reverse('admin:index'),
            'has_module_permission': True,
            'models': [{
                'name': 'Ассеты и Фильтрация',
                'object_name': 'observer_assets_view',
                'admin_url': reverse('observer_assets:assets_overview'),
                'add_url': None,
                'has_add_permission': False,
                'has_change_permission': True,
                'has_delete_permission': False,
            }],
        }
        app_list.append(observer_app)
        return app_list


# Регистрируем кастомную админ-панель
admin_site = ObserverAssetsAdminSite(name='observer_assets_admin')

# Если есть модели - регистрируем их
try:
    from .models import ObserverSettings
    admin_site.register(ObserverSettings)
except ImportError:
    pass
