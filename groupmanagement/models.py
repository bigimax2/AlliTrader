from django.contrib.auth.models import User, Group
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from authenticated.models import State


class NiceGroup(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, primary_key=True, related_name='nicegroup')
    users = models.ManyToManyField(User, blank=True, related_name='groupuser')
    group_leaders = models.ManyToManyField(User, blank=True, related_name='groupleaders')
    states = models.ManyToManyField(State,blank=True, related_name='groupstate')
    description = models.TextField(blank=True, max_length=500)

    class Meta:

        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def is_group_leaders(self, user):
        """Проверяет, является ли пользователь админом или модератором группы."""
        return user in self.group_leaders.all()

    def is_member(self, user):
        """Проверяет, состоит ли пользователь в группе."""
        return user in self.users.all()

    def remove_user(self, user):
        if user in self.users.all():
            self.users.remove(user)
        GroupApplication.objects.filter(user=user, group=self).delete()

    def __str__(self):
        return self.group.name



class GroupApplication(models.Model):
    """
    Модель для подачи заявки пользователя в группу NiceGroup.
    """
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Ожидает рассмотрения'),
        (APPROVED, 'Одобрена'),
        (REJECTED, 'Отклонена'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    group = models.ForeignKey('NiceGroup', on_delete=models.CASCADE, verbose_name='Группа')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField('Дата подачи', default=timezone.now)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Заявка в группу'
        verbose_name_plural = 'Заявки в группы'
        unique_together = ('user', 'group')  # Один пользователь — одна активная заявка на группу
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} → {self.group.group.name} ({self.get_status_display()})'