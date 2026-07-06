from django.urls import path

from observer_assets_all import views

app_name = 'observer_assets_all'
urlpatterns = [
    path('assets_overview/', views.assets_overview, name='assets_overview'),
    path('type_names_lookup/', views.type_names_lookup, name='type_names_lookup'),
    path('type_names_lookup/delete/', views.delete_selected_type_search_results, name='delete_selected_type_search_results'),
]