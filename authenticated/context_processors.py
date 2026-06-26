from authenticated.models import Notification
from core.registry import app_registry


def user_app_access(request):
    """
    Контекстный процессор для шаблонов.
    
    Добавляет в контекст шаблонов информацию о приложениях, 
    доступных текущему пользователю.
    
    Логика:
    - Суперпользователь видит все зарегистрированные приложения.
    - Обычные пользователи — только те, на которые у них есть разрешения через state.
    
    Возвращаемые переменные:
    - user_app_labels: множество (set) строк с app_label доступных приложений.
    - user_apps: список словарей с данными о приложениях (для отображения в сайдбаре).
    """
    # Инициализация множества для хранения app_label доступных приложений
    app_labels = set()
    
    # Инициализация списка для хранения данных о приложениях (для интерфейса)
    user_apps = []

    # Получаем глобальную конфигурацию всех зарегистрированных приложений
    APP_CONFIG = app_registry.get_apps()

    # Проверяем, авторизован ли пользователь
    if request.user.is_authenticated:
        # Если пользователь — суперпользователь, даём доступ ко всем приложениям
        if request.user.is_superuser:
            app_labels = set(APP_CONFIG.keys())
        else:
            # Обычный пользователь: проверяем доступ через state и права
            try:
                state = request.user.userprofile.state
                app_labels = {
                    perm.content_type.app_label
                    for perm in state.permissions.all()
                    if perm.content_type.app_label in APP_CONFIG
                }
            except (AttributeError, Exception):
                # На случай отсутствия профиля или state — доступа нет
                app_labels = set()

        # Формируем список приложений для интерфейса
        user_apps = [
            {
                'name': config['name'],
                'icon': config['icon'],
                'url': config['url'],
            }
            for label, config in APP_CONFIG.items()
            if label in app_labels
        ]

    return {
        'user_app_labels': app_labels,
        'user_apps': user_apps,
    }

def notification_counters(request):
    """
    Добавляет информацию о непрочитанных уведомлениях в контекст.
    """
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'latest_notifications': [],
        }

    # Получаем непрочитанные уведомления текущего пользователя
    unread = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')

    return {
        'unread_notifications_count': unread.count(),
        'latest_notifications': unread[:5],  # последние 5
    }