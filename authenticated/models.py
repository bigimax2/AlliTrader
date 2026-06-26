from django.contrib.auth.models import Permission, User
from django.db import models
from jsonschema.exceptions import ValidationError
from django.utils import timezone

from eveonline.models import EveCharacter, EveCorporation, EveAlliance


class State(models.Model):
    name = models.CharField(max_length=32, blank=False, null=False, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    member_characters = models.ManyToManyField(EveCharacter, blank=True)
    member_corporations = models.ManyToManyField(EveCorporation, blank=True)
    member_alliance = models.ManyToManyField(EveAlliance, blank=True)
    priority = models.IntegerField(unique=True)


    class Meta:
        verbose_name = "Состояние"
        verbose_name_plural = "Состояния"

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        if State.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(f"State с именем '{self.name}' уже существует.")
        super().save(*args, **kwargs)

    def get_related_objects(self, field_name):

        if not hasattr(self, field_name):
            raise ValueError(f"Поле '{field_name}' не существует в модели State.")

        related_field = getattr(self, field_name)
        return related_field.all()

    def has_access_to_app(self, app_label):
        """
        Проверяет, имеет ли этот State доступ к приложению по app_label.
        Если State имеет хотя бы одно разрешение из этого приложения — доступ есть.
        """
        return self.permissions.filter(content_type__app_label=app_label).exists()

def get_guest_state():
    try:
        return State.objects.get(name='Guest')
    except State.DoesNotExist:
        return State.objects.create(name='Guest', priority=0)


def get_guest_state_pk():
    return get_guest_state().pk


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.SET_DEFAULT, default=get_guest_state_pk, verbose_name='Состояние',)
    main_character = models.OneToOneField(EveCharacter, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Основной персонаж',)

    class Meta:

        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"



    def __str__(self):
        return str(self.user)

class Notification(models.Model):
    """Модель для уведомлений о действиях пользователей и системных событиях"""
    
    # Типы уведомлений
    USER_ACTION = 'user_action'
    SYSTEM = 'system'
    TYPE_CHOICES = [
        (USER_ACTION, 'Действие пользователя'),
        (SYSTEM, 'Системное событие'),
    ]
    
    # Поля модели
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255, verbose_name='Сообщение')
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=USER_ACTION,
        verbose_name='Тип уведомления'
    )
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    
    # Дополнительные данные для системных уведомлений
    system_message = models.BooleanField(default=False, verbose_name='Системное сообщение')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f'{self.user.username}: {self.message}'


class OwnershipRecord(models.Model):
    character = models.ForeignKey(EveCharacter, on_delete=models.CASCADE, related_name='ownership_records',
                                  verbose_name='Персонаж')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ownership_records',
                             verbose_name='Пользователь')
    created = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Владелец персонажа'
        verbose_name_plural = 'Владелец персонажей'
        ordering = ['-created']

    def __str__(self):
        return f"{self.user}: {self.character} on {self.created}"