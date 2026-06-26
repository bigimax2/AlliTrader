from django.urls import path
from messenger import views

app_name = 'messenger'
urlpatterns = [
    path('', views.render_messenger_template, name='render_messenger_template'),
    path('registration_user/', views.registration_user_messenger, name='registration_user_messenger'),
    path('create_server/', views.create_server_messenger, name='create_server_messenger'),
    path('conection_to_messenger/', views.connection_to_messenger, name='connection_to_messenger'),
]