from django.urls import path

from observer_assets_all import views

app_name = 'observer_assets_all'
urlpatterns = [
    path('assets_overview/', views.assets_overview, name='assets_overview'),
    path('save_asset_notes/', views.save_asset_notes, name='save_asset_notes'),

]