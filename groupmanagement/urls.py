from django.urls import path

from groupmanagement import views

app_name = 'groupmanagement'
urlpatterns = [
    path('groups/', views.render_group, name='groups'),
    path('groups/<int:group_id>/leave/', views.levi_group, name='leave_group'),
    path('groups/<int:group_id>/apply/', views.apply_to_group, name='apply_to_group'),
    path('groups/<int:group_id>/applications/', views.group_applications, name='group_applications'),
    path('group/<int:group_id>/members/', views.group_members, name='group_members'),
    path('group/<int:group_id>/remove-member/<int:user_id>/', views.remove_member, name='remove_member'),
    path('applications/<int:application_id>/approve/', views.approve_application, name='approve_application'),
    path('applications/<int:application_id>/reject/', views.reject_application, name='reject_application'),
]