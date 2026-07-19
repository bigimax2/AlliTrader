from django.urls import path

from traders import views

app_name = 'traders'
urlpatterns = [
    path('type_names_lookup/', views.type_names_lookup, name='type_names_lookup'),
    path('type_names_lookup/delete/', views.delete_selected_type_search_results, name='delete_selected_type_search_results'),
    path('save_coefficient/', views.save_coefficient, name='save_coefficient'),
]