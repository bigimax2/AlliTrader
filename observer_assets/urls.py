from django.urls import path

from observer_assets import views

app_name = 'observer_assets'
urlpatterns = [
    path('assets_overview/', views.assets_overview, name='assets_overview'),
]