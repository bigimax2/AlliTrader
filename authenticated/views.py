from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from esi.decorators import token_required
from django.conf import settings
from authenticated.auth_in_portal import authinportal
from authenticated.models import OwnershipRecord, UserProfile, Notification
from authenticated.signals import assign_states_periodically
from authenticated.notification_service import NotificationService

from groupmanagement.models import NiceGroup


@token_required(new=True, scopes=settings.ENABLES_SCOPES)
def get_token(request, token):
    status = authenticate(request, token=token)

    authinportal(request, token=token,)
    return redirect ('authenticated:profile')

@login_required
def render_profile(request):
    user = request.user
    main_pers = None

    try:
        if user.userprofile:
            main_pers = user.userprofile.main_character
    except UserProfile.DoesNotExist:
        # Если профиля нет — перенаправляем на создание, а не на логин!
        return render(request, 'log_in_portal.html')
    o_r = OwnershipRecord.objects.filter(user_id=user.id)
    user_groups = NiceGroup.objects.filter(users=request.user)

    return render(request, 'profile.html', context={'main_pers': main_pers, 'o_r': o_r, 'user_groups': user_groups,})

def login_user(request):
    if request.user.is_authenticated:
        return redirect('authenticated:profile')
    return render(request, 'log_in_portal.html')

def logout_user(request):
    logout(request)
    return render(request, 'log_in_portal.html')

def change_main_personage(request, user_id, personage_id):
    try:
        user_profile = get_object_or_404(UserProfile, user_id=user_id)
        user_profile.main_character_id = personage_id
        user_profile.save()
        assign_states_periodically(user_id)
        # Создаем уведомление о смене основного персонажа
        NotificationService.create_user_action(
            user=user_profile.user,
            message=f'Изменен основной персонаж на {user_profile.main_character.name}'
        )
        return redirect('authenticated:profile')

    except ObjectDoesNotExist:
        return render(request, 'error.html', {'error': 'User profile not found.'})

    except Exception as e:
        return render(request, 'error.html',
                      {'error': f'An error occurred while changing the main character: {str(e)}'})


@login_required
def get_notifications(request):
    """Получение уведомлений для текущего пользователя"""
    user = request.user
    # Проверяем, нужно ли отметить все уведомления как прочитанные
    mark_all_read = request.GET.get('mark_all_read', 'false').lower() == 'true'
    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    if mark_all_read:
        # Отмечаем все непрочитанные уведомления пользователя как прочитанные
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    
    # Суперпользователи видят непрочитанные уведомления и системные сообщения
    if user.is_superuser:
        notifications = Notification.objects.filter(
            models.Q(user=user, is_read=False) | 
            models.Q(system_message=True, is_read=False)
        ).order_by('-created_at')[:10]
    else:
        # Обычные пользователи видят только свои непрочитанные уведомления
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Применяем поиск, если указан запрос
    if search_query:
        notifications = notifications.filter(
            models.Q(message__icontains=search_query) | 
            models.Q(type__icontains=search_query)
        )
    
    # Преобразуем уведомления в формат JSON
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'message': notification.message,
            'type': notification.get_notification_type_display(),
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'is_system': notification.system_message
        })
    
    # Обновляем счетчик непрочитанных уведомлений
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': unread_count,
        'search_query': search_query
    })


@login_required
def mark_notification_read(request, notification_id):
    """Отмечает конкретное уведомление как прочитанное"""
    user = request.user

    try:
        notification = Notification.objects.get(id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Уведомление не найдено'}, status=404)


@login_required
def delete_notification(request, notification_id):
    """Удаляет конкретное уведомление"""
    user = request.user

    try:
        notification = Notification.objects.get(id=notification_id, user=user)
        notification.delete()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Уведомление не найдено'}, status=404)


@login_required
def delete_all_notifications(request):
    """Удаляет все уведомления пользователя"""
    user = request.user
    
    try:
        Notification.objects.filter(user=user).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def notifications_page(request):
    """Отображает страницу со всеми уведомлениями пользователя"""
    return render(request, 'notifications.html')