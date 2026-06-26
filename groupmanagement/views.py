from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from authenticated.notification_service import NotificationService
from .models import NiceGroup, GroupApplication
from .tasks import check_nicegroup_user_states


@login_required
def render_group(request):
    """
    Отображает группы, в которых состоит пользователь,
    и доступные для вступления группы.
    """
    user_profile = getattr(request.user, 'userprofile', None)

    if not user_profile:
        messages.error(request, "Профиль пользователя не найден.")
        return redirect('some_profile_setup_url')  # Замените на нужный

    if not hasattr(user_profile, 'state') or not user_profile.state:
        messages.warning(request, "Не указан регион (state) для доступа к группам.")
        user_state = None
    else:
        user_state = user_profile.state

    # Группы пользователя
    user_groups = NiceGroup.objects.filter(users=request.user).prefetch_related('users', 'group_leaders')

    # Доступные для вступления группы (в регионе пользователя, но без него)
    available_groups = (
        NiceGroup.objects
        .filter(states=user_state)
        .exclude(users=request.user)
        .prefetch_related('users', 'group_leaders')
    )

    # Добавляем флаг лидерства
    for group in user_groups:
        group.is_leader = group.is_group_leaders(request.user)  # вызываем метод в view

    #update_eve_entities()
    check_nicegroup_user_states()

    context = {
        'user_groups': user_groups,
        'available_groups': available_groups,
        'has_user_groups': user_groups.exists(),
        'has_available_groups': available_groups.exists(),
        'user_id': request.user.id,
        'page': 'my_groups',
    }
    return render(request, 'groups.html', context)


@login_required
def group_applications(request, group_id):
    """
    Показывает заявки в конкретную группу.
    Доступно только лидерам группы.
    """
    group = get_object_or_404(NiceGroup, pk=group_id)

    if not group.is_group_leaders(request.user):
        messages.error(request, 'У вас нет прав на просмотр заявок этой группы.')
        return redirect('groupmanagement:groups')

    applications = GroupApplication.objects.filter(
        group=group
    ).select_related('user').order_by('-created_at')

    context = {
        'group': group,
        'applications': applications,
        'page': 'group_applications',
    }
    return render(request, 'group_applications.html', context)


@login_required
@require_http_methods(["POST"])
def apply_to_group(request, group_id):
    """
    Подача заявки в группу.
    """
    group = get_object_or_404(NiceGroup, pk=group_id)

    existing_application = GroupApplication.objects.filter(
        user=request.user,
        group=group
    ).first()

    if existing_application:
        if existing_application.status == GroupApplication.PENDING:
            messages.warning(request, 'Вы уже отправили заявку в эту группу. Ожидайте ответа.')
        elif existing_application.status == GroupApplication.APPROVED:
            messages.info(request, 'Вы уже состоите в этой группе.')
        elif existing_application.status == GroupApplication.REJECTED:
            # Повторная подача после отказа
            existing_application.status = GroupApplication.PENDING
            existing_application.created_at = timezone.now()
            existing_application.save()
            messages.success(request, 'Заявка повторно отправлена.')
    else:
        GroupApplication.objects.create(
            user=request.user,
            group=group,
            status=GroupApplication.PENDING
        )
        messages.success(request, 'Заявка на вступление отправлена.')

    return redirect('groupmanagement:groups')


@login_required
@require_http_methods(["POST"])
def levi_group(request, group_id):
    """
    Покинуть группу.
    """
    group = get_object_or_404(NiceGroup, pk=group_id)
    group.remove_user(request.user)

    messages.success(request, 'Вы покинули группу.')
    return redirect('groupmanagement:groups')


@login_required
@require_http_methods(["POST"])
def approve_application(request, application_id):
    """
    Одобрить заявку.
    """
    application = get_object_or_404(GroupApplication, id=application_id)
    group = application.group


    if not group.is_group_leaders(request.user):
        messages.error(request, 'У вас нет прав для одобрения заявок.')
        return redirect('groupmanagement:group_applications', group_id=group.id)

    with transaction.atomic():
        # Добавляем пользователя в группу (через M2M)
        group.users.add(application.user)
        # Добавляем в auth.Group
        django_group = group.group  # Это auth.Group
        django_group.user_set.add(application.user)

        application.status = GroupApplication.APPROVED
        application.save()


    messages.success(request, f'Пользователь {application.user.username} добавлен в группу.')
    NotificationService.create_user_action(user=request.user, message=f"Заявка от {application.user.username} принята.")
    return redirect('groupmanagement:group_applications', group_id=group.group.id)


@login_required
@require_http_methods(["POST"])
def reject_application(request, application_id):
    """
    Отклонить заявку.
    """
    application = get_object_or_404(GroupApplication, id=application_id)
    group = application.group

    if not group.is_group_leaders(request.user):
        messages.error(request, 'У вас нет прав для отклонения заявок.')
        return redirect('groupmanagement:group_applications', group_id=group.id)

    application.status = GroupApplication.REJECTED
    application.save()


    messages.info(request, f'Заявка от {application.user.username} отклонена.')
    NotificationService.create_user_action(user=application.user, message=f"Заявка от {application.user.username} отклонена.")
    NotificationService.create_user_action(user=request.user,message=f"Заявка от {application.user.username} отклонена.")
    NotificationService.create_system_message(user=request.user, message=f"Заявка от {application.user.username} отклонена.")
    return redirect('groupmanagement:group_applications', group_id=group.id)

@login_required
def group_members(request, group_id):
    """
    Отображает список участников группы.
    Доступно только лидерам группы.
    Лидер может исключить участника (кроме себя и других лидеров).
    """
    group = get_object_or_404(NiceGroup, pk=group_id)

    if not group.is_group_leaders(request.user):
        messages.error(request, 'У вас нет прав на управление составом группы.')
        return redirect('groupmanagement:groups')

    members = group.users.all().prefetch_related('userprofile').order_by('username')
    leaders = group.group_leaders.all()

    context = {
        'group': group,
        'members': members,
        'leaders': leaders,
        'page': 'group_members',
    }
    return render(request, 'group_members.html', context)

@login_required
@require_http_methods(["POST"])
@transaction.atomic
def remove_member(request, group_id, user_id):
    """
    Исключить участника из группы (лидером группы).
    Нельзя исключить самого себя или других лидеров.
    """
    group = get_object_or_404(NiceGroup, pk=group_id)

    if not group.is_group_leaders(request.user):
        messages.error(request, 'У вас нет прав для управления составом группы.')
        return redirect('groupmanagement:groups')

    member_to_remove = get_object_or_404(group.users, pk=user_id)

    # Проверяем, можно ли удалить
    if member_to_remove == request.user:
        messages.warning(request, 'Нельзя исключить самого себя из группы. Используйте "Покинуть группу".')
    elif group.is_group_leaders(member_to_remove):
        messages.warning(request, 'Нельзя исключить другого лидера группы.')
    else:
        group.remove_user(member_to_remove)
        NotificationService.create_user_action(user=member_to_remove,
                                               message=f"Заявка от {member_to_remove} отклонена.")
        NotificationService.create_user_action(user=request.user,
                                               message=f"Заявка от {member_to_remove} отклонена.")
        NotificationService.create_system_message(user=request.user,
                                                  message=f"Заявка от {member_to_remove} отклонена.")
        messages.success(request, f'Пользователь {member_to_remove.username} исключён из группы.')

    return redirect('groupmanagement:group_members', group_id=group.group_id)