from django.urls import path

from observer_assets_single import views

app_name = 'observer_assets_single'
urlpatterns = [
    path('render_traders/', views.render_traders, name='render_traders'),

    path('get_token_assets/', views.get_token_assets, name='get_token_assets'),
    path('alert_settings/', views.alert_settings, name='alert_settings'),
    path('delete_threshold/', views.delete_threshold, name='delete_threshold'),
    path('edit_threshold/', views.edit_threshold, name='edit_threshold'),
    path('export_alerts/', views.export_alerts, name='export_alerts'),
    path('import_alerts/', views.import_alerts, name='import_alerts'),

]
