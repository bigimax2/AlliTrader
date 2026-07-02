import os


class AppRegistry:
    """Реестр приложений для сайдбара и меню."""
    def __init__(self):
        self._apps = {}

    def register(self, app_label: str, config: dict):
        if config is None:
            # Можно добавить проверку окружения, чтобы уточнить причину
            if os.environ.get('RUN_MAIN') == 'true':
                reason = 'отключено в настройках'
            else:
                reason = 'Reloader-процесс'
            print(f"[AppRegistry] Пропущено приложение '{app_label}' — {reason}.")
            return
        """
        Регистрирует приложение.
        :param app_label: строка (например, 'discord')
        :param config: словарь с полями: 'name', 'icon', 'url'
        :raises ValueError: если приложение уже зарегистрировано
        """
        if app_label in self._apps:
            raise ValueError(f"Приложение '{app_label}' уже зарегистрировано: {self._apps[app_label]}")

        required_keys = {'name', 'icon', 'url'}
        if not required_keys.issubset(config.keys()):
            raise ValueError(f"Для '{app_label}' не хватает ключей: {required_keys - config.keys()}")

        self._apps[app_label] = config
        # Отключаем вывод для избежания проблем с Unicode в Windows cmd
        # print(f"[AppRegistry] Registered app: {app_label}")

    def get_apps(self):
        """Возвращает копию словаря зарегистрированных приложений."""
        return self._apps.copy()

    def unregister(self, app_label: str):
        """Удаляет приложение из реестра (для тестов или перерегистрации)."""
        self._apps.pop(app_label, None)

    def is_registered(self, app_label: str) -> bool:
        """Проверяет, зарегистрировано ли приложение."""
        return app_label in self._apps

    def decorator(self, app_label: str):
        """
        Декоратор для регистрации конфигурации приложения.
        Пример:
            @app_registry.decorator('discord')
            def get_config():
                return {
                    'name': 'Дискорд',
                    'icon': 'fa-user-group',
                    'url': 'discord:discord-info',
                }
        """
        def wrapper(func):
            config = func()
            self.register(app_label, config)
            return func  # возвращаем оригинальную функцию (для повторного вызова не нужно)
        return wrapper


# Глобальный реестр
app_registry = AppRegistry()