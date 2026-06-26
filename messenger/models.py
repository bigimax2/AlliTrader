from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import Q

from authenticated.models import State


class MemberMessenger(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    link_url = models.URLField()
    refresh_token = models.TextField()
    access_token = models.TextField()
    token = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)
    messenger_user = models.TextField()
    messenger_user_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class MessengerServerManager(models.Manager):
    def accessible_by_user(self, user):
        if not user.is_authenticated:
            return self.none()

        user_groups = user.groups.all()
        profile = getattr(user, 'userprofile', None)
        current_state = getattr(profile, 'state', None)

        # Убираем "доступно всем" при (group=None и state=None)
        # Оставляем только те записи, где хотя бы одно из полей НЕ None
        base_filters = (
            Q(allowed_groups__group__in=user_groups) | Q(allowed_groups__group__isnull=True),
            Q(allowed_groups__state=current_state) | Q(allowed_groups__state__isnull=True)
        )

        # Исключаем случаи, когда и group, и state — None одновременно
        # То есть: не разрешаем доступ, если ServerAccessGroup(group=None, state=None)
        qs = self.filter(*base_filters).exclude(
            allowed_groups__group__isnull=True,
            allowed_groups__state__isnull=True
        ).distinct()

        return qs

class MessengerServer(models.Model):
    objects = MessengerServerManager()
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=True, blank=True)
    server_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    invite_link = models.URLField()
    invite_token = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.owner.username

class ServerAccessGroup(models.Model):
    server = models.ForeignKey(MessengerServer, on_delete=models.CASCADE, related_name='allowed_groups')
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE, related_name='allowed_servers')
    state = models.ForeignKey(State, null=True, blank=True , on_delete=models.CASCADE, related_name='allowed_states')

    class Meta:
        unique_together = ('server', 'group', 'state')  # Одинаковая группа не может быть добавлена дважды
        verbose_name = "Доступ группы к серверу"
        verbose_name_plural = "Доступы групп к серверам"

    def __str__(self):
        group_name = self.group.name if self.group else "Все группы"
        state_name = self.state.name if self.state else "Любое состояние"
        return f"{group_name} → {self.server.name} ({state_name})"