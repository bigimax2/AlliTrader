from datetime import datetime
from django.utils import timezone
from authenticated.models import Notification, User

class NotificationService:
    """
    Сервис для создания и управления уведомлениями.
    Инкапсулирует логику создания уведомлений, позволяя вызывать её
    через простые методы с указанием пользователя, сообщения, типа и статуса.
    """

    @staticmethod
    def create_notification(
        user: User,
        message: str,
        notification_type: str = Notification.USER_ACTION,
        is_system: bool = False,
        is_read: bool = False,
        created_at: datetime = None
    ):
        """
        Создаёт новое уведомление.

        :param user: Пользователь, которому отправляется уведомление
        :param message: Текст уведомления
        :param notification_type: Тип уведомления (USER_ACTION или SYSTEM)
        :param is_system: Является ли уведомление системным
        :param is_read: Статус прочтения
        :param created_at: Время создания (по умолчанию — сейчас)
        :return: Объект Notification
        """
        notification = Notification.objects.create(
            user=user,
            message=message,
            notification_type=notification_type,
            system_message=is_system,
            is_read=is_read,
            created_at=created_at or timezone.now()
        )
        return notification

    @classmethod
    def create_user_action(cls, user: User, message: str, is_read: bool = False):
        """
        Создаёт уведомление о действии пользователя.
        """
        return cls.create_notification(
            user=user,
            message=message,
            notification_type=Notification.USER_ACTION,
            is_system=False,
            is_read=is_read
        )

    @classmethod
    def create_system_message(cls, user: User, message: str, is_read: bool = False):
        """
        Создаёт системное уведомление для пользователя.
        """
        return cls.create_notification(
            user=user,
            message=message,
            notification_type=Notification.SYSTEM,
            is_system=True,
            is_read=is_read
        )
