from django.urls import path

from authenticated import views

app_name = 'authenticated'

urlpatterns = [
    path('get-token/', views.get_token, name='get-token'),
    path('profile/', views.render_profile, name='profile'),
    path('', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('change_main_personage/<int:user_id>/<int:personage_id>/', views.change_main_personage, name='change_main_personage'),
    path('get_notifications/', views.get_notifications, name='get_notifications'),
    path('mark_notification_read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('delete_notification/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('delete_all_notifications/', views.delete_all_notifications, name='delete_all_notifications'),
    path('notifications/', views.notifications_page, name='notifications_page'),
]