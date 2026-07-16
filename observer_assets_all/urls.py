from django.urls import path

from observer_assets_all import views

app_name = 'observer_assets_all'
urlpatterns = [
    path('assets_overview/', views.assets_overview, name='assets_overview'),

]