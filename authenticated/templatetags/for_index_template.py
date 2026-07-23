from django import template

register = template.Library()

@register.inclusion_tag('menu.html', takes_context=True)
def get_img_main_personage(context):
    # Получаем пользователя из контекста запроса
    user = context.request.user

    # Получаем основного персонажа пользователя из профиля
    main_personage = user.userprofile.main_character

    # Получаем набор меток приложений из контекста (по умолчанию — пустое множество)
    user_app_labels = context.get('user_app_labels', set())

    # Получаем набор приложений пользователя из контекста (по умолчанию — пустое множество)
    user_apps = context.get('user_apps', set())
    
    unread_notifications_count = context.get('unread_notifications_count', 0)
    latest_notifications = context.get('latest_notifications', [])
    
    # Добавляем данные для dropdown писем
    mail_labels = context.get('mail_labels', [])
    unread_messages_count = context.get('unread_messages_count', 0)
    latest_messages = context.get('latest_messages', [])

    # Возвращаем словарь с данными, которые будут использоваться в шаблоне menu.html
    return {
        'main_personage': main_personage,
        'user_app_labels': user_app_labels,
        'user_apps': user_apps,
        'unread_notifications_count': unread_notifications_count,
        'latest_notifications': latest_notifications,
        'mail_labels': mail_labels,
        'unread_messages_count': unread_messages_count,
        'latest_messages': latest_messages,
        'user': user,
    }
