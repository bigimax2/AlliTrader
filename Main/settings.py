
import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

# Убран импорт CELERY_BEAT_SCHEDULE из config.celery_schedule
# Он будет загружен в celery.py после инициализации Django
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = BASE_DIR / '.env'  # предполагаем, что .env лежит в корне проекта (выше Nice3)
load_dotenv(dotenv_path=ENV_PATH)

# Загружаем .env, если он существует
if not ENV_PATH.exists():
    import sys
    print(f"⚠️  Файл окружения не найден: {ENV_PATH}", file=sys.stderr)

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost').split(',') if host.strip()]
print(f'{ALLOWED_HOSTS}')

CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:8000", "https://*.cloudpub.ru/",]
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True


# Application definition


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'django_celery_results',
    'core',
    'config',
    'eveonline.apps.EveonlineConfig',
    'esi.apps.EsiConfig',
    'authenticated.apps.AutenticatedConfig',
    'groupmanagement.apps.GroupmanagementConfig',
    'channels',
    'trader.apps.TraderConfig',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

]

ROOT_URLCONF = 'Main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'authenticated.context_processors.user_app_access',
                'authenticated.context_processors.notification_counters'
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

WSGI_APPLICATION = 'Main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ESI_SSO_CLIENT_ID = os.getenv('ESI_SSO_CLIENT_ID')
ESI_SSO_CLIENT_SECRET = os.getenv('ESI_SSO_CLIENT_SECRET')
ESI_SSO_CALLBACK_URL = os.getenv('ESI_SSO_CALLBACK_URL')



ESI_USER_CONTACT_EMAIL= 'email@example.com'
ENABLES_SCOPES = ['publicData', 'esi-characters.read_corporation_roles.v1']

ENABLE_DISCORD = os.getenv('ENABLE_DISCORD', '').strip().lower() in ('true', 'on', '1', 'yes')

DISCORD_APPLICATION_ID = os.getenv('DISCORD_APPLICATION_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', '')
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')


LOGIN_URL = 'authenticated:login'
LOGIN_REDIRECT_URL = 'authenticated:login'
LOGOUT_REDIRECT_URL = 'authenticated:login'

USE_CELERY = os.getenv('USE_CELERY', '').strip().lower() in ('true', 'on', '1', 'yes')

CELERY_BROKER_URL = "redis://127.0.0.1:6379/1"  # URL для подключения к брокеру сообщений Celery
CELERY_TIMEZONE = TIME_ZONE  # Часовой пояс для Celery
CELERY_TASK_TRACK_STARTED = True  # Отслеживание начала выполнения задачи

CELERY_RESULT_BACKEND = "django-db"  # Бэкенд результатов для Celery
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_RESULT_EXTENDED = True  # Расширенные результаты для Celery

# Опционально: автоочистка результатов старше 1 дня
CELERY_RESULT_EXPIRES = 86400  # 24 часа

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

SDE_API_URL = 'https://api.niceplatform.ru/'
SDE_API_KEY = os.getenv('SDE_API_KEY', '1KOgsy93GmqEEmcpVfFKl9IaHpOVRt9uofyxik11OG2uZJNOd5Ja34tmJ2u5m7X6asVMHHzDHarS1VH91rMm88LTpq0FG9xIuefziT7JgR87RoQkcbrOMx3ISvb4ep1j06kPugZJK844XbGUhuVRcSSdOVwYJ97N3O6o4A0VvNm4TpUVkdeb5lISSZRUrv7UklnRXjkJrdGVstEU8QHxZ5p9AGEu0hH6wqDOzdOKMtDtR9ZV56F3JaOOpoVKjFfz')

# Логирование
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'log/app.log',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

ENABLE_TRADER = os.getenv('ENABLE_TRADER', '').strip().lower() in ('true', '1', 'yes')