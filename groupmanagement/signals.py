from django.contrib.auth.models import User, Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from groupmanagement.models import GroupApplication, NiceGroup
from authenticated.models import UserProfile


@receiver(m2m_changed, sender=NiceGroup.users.through)
def sync_with_auth_group(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        for user_id in pk_set:
            user = instance.users.get(pk=user_id)
            instance.group.user_set.add(user)  # Добавляем в auth.Group
    elif action == 'post_remove':
        for user_id in pk_set:
            user = User.objects.get(pk=user_id)
            instance.group.user_set.remove(user)  # Удаляем из auth.Group
    elif action == 'post_clear':
        # При очистке всех пользователей из NiceGroup, удаляем всех из auth.Group
        instance.group.user_set.clear()  # Удаляем всех из auth.Group

@receiver(m2m_changed, sender=NiceGroup.states.through)
def handle_states_change(sender, instance, action, pk_set, **kwargs):
    """
    Обработчик изменений в связях states группы.
    Когда state удаляется из видимости группы, все пользователи из этого state
    автоматически удаляются из группы.
    """
    if action == 'post_remove':
        # States были удалены из группы
        removed_states = pk_set
        
        # Находим всех пользователей, принадлежащих удаленным states
        users_to_remove = []
        for state_id in removed_states:
            users_with_state = User.objects.filter(
                userprofile__state__id=state_id
            )
            users_to_remove.extend(users_with_state)
        
        # Удаляем пользователей из группы
        for user in users_to_remove:
            if instance.is_member(user):
                instance.remove_user(user)
                
    elif action == 'post_clear':
        # Все states были удалены из группы
        # Удаляем всех пользователей из группы
        for user in instance.users.all():
            instance.remove_user(user)