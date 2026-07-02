from django.urls import path

from trader import views

app_name = 'trader'
urlpatterns = [
    path('render_traders/', views.render_traders, name='render_traders'),

    path('get_token_assets/', views.get_token_assets, name='get_token_assets'),
    path('alert_settings/', views.alert_settings, name='alert_settings'),
    path('delete_threshold/', views.delete_threshold, name='delete_threshold'),

]
