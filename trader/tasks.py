import logging
from django.apps import apps
from core.app_task import app_task
from trader.scopes_for_traders import SCOPES_FOR_TRADERS
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


@app_task()
def get_personage_assets(token_id=None):
    from esi.models import Token
    from eveonline.models import EveCharacter
    from trader.models import Asset
    eveonline_config = apps.get_app_config('eveonline')
    esi = eveonline_config.esi

    required_scopes = set(SCOPES_FOR_TRADERS)
    tokens = []

    if token_id:
        try:
            token = Token.objects.get(pk=token_id)
            tokens = [token]
            logger.info(f"Получен token с ID {token_id}")
        except Token.DoesNotExist:
            logger.error(f"Token с ID {token_id} не существует.")
            return []
    else:
        tokens = Token.objects.filter(
            scopes__name__in=required_scopes
        ).distinct()
        logger.info(f"Найдено {tokens.count()} токенов с необходимыми scopes")

    for token in tokens:
        token_scopes = set(token.scopes.all().values_list('name', flat=True))
        if not required_scopes.issubset(token_scopes):
            logger.warning(f"Token {token.pk} не хватает scope'ов: {required_scopes - token_scopes}")
            continue

        try:
            eve_char = EveCharacter.objects.get(character_id=token.character_id)
        except EveCharacter.DoesNotExist:
            logger.error(f"EveCharacter с character_id {token.character_id} не найден.")
            continue
        
        try:
            logger.info(f"Получение ассетов для {eve_char.name} (ID: {eve_char.character_id})")
            
            # Проверяем, есть ли ассеты в БД
            has_assets_in_db = Asset.objects.filter(character=eve_char).exists()
            logger.info(f"Есть ли записи в бд {has_assets_in_db}")
            
            assets_response = esi.client.Assets.GetCharactersCharacterIdAssets(
                character_id=eve_char.character_id, token=token)
            
            # Пытаемся получить результаты
            try:
                assets_response_data = assets_response.results()
                # Если результат - это HttpResponse, берем .data
                if hasattr(assets_response_data, 'data'):
                    assets_data = [dict(item) for item in assets_response_data.data]
                else:
                    assets_data = [dict(item) for item in assets_response_data]
                logger.info(f"Получены данные ассетов из API для {eve_char.name}")
            except Exception as e:
                if "HTTPNotModified" in str(type(e)) or "304" in str(e):
                    logger.info(f"Ассеты не изменились для {eve_char.name}, используем данные из БД")
                    # Если данные не изменились и БД не пуста - не запускаем parser_assets
                    if has_assets_in_db:
                        logger.info(f"Пропускаем обработку для {eve_char.name}, данные не изменились")
                        continue
                    # Если БД пуста, делаем повторный запрос
                    logger.info(f"БД пуста, делаем повторный запрос с force_refresh для {eve_char.name}")
                    assets_response = esi.client.Assets.GetCharactersCharacterIdAssets(
                        character_id=eve_char.character_id, token=token)
                    assets_response_data = assets_response.results(force_refresh=True)
                    if hasattr(assets_response_data, 'data'):
                        assets_data = [dict(item) for item in assets_response_data.data]
                    else:
                        assets_data = [dict(item) for item in assets_response_data]
                else:
                    raise e
            
            from trader.views import parser_assets
            parser_assets(assets_data, eve_char)
            logger.info(f"Ассеты успешно получены и обработаны для {eve_char.name}")
        except Exception as e:
            logger.exception(f"Ошибка получения ассетов у {eve_char.name} (ID: {eve_char.character_id}): {str(e)}")
    return True


@app_task()
def deploy_task():
    """Асинхронная задача для выполнения деплоя"""
    logger.info("Starting deploy task...")
    
    PROJECT_PATH = Path('/var/www/allitrader')
    VIRTUALENV_PATH = PROJECT_PATH / '.venv'
    MANAGE_PY = PROJECT_PATH / 'manage.py'
    LOG_FILE = PROJECT_PATH / 'deploy.log'
    
    # Настройка переменных окружения
    os.environ.setdefault('PROJECT_NAME', 'Main')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main.settings')
    
    try:
        # 1. git pull
        logger.info("Updating code from repository...")
        result = subprocess.run(
            ['git', 'pull', 'origin', 'master'],
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Git pull result: {result.stdout}")
        
        # 2. Установка зависимостей
        logger.info("Installing dependencies...")
        pip_bin = VIRTUALENV_PATH / 'bin' / 'pip'
        result = subprocess.run(
            [str(pip_bin), 'install', '-r', str(PROJECT_PATH / 'requirements.txt')],
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.warning(f"Failed to install dependencies: {result.stderr}")
        else:
            logger.info("Dependencies installed successfully")
        
        # 3. Применение миграций
        logger.info("Running migrations...")
        python_bin = VIRTUALENV_PATH / 'bin' / 'python'
        result = subprocess.run(
            [str(python_bin), str(MANAGE_PY), 'migrate', '--noinput'],
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.warning(f"Failed to run migrations: {result.stderr}")
        else:
            logger.info("Migrations completed")
        
        # 4. Сборка статики
        logger.info("Collecting static files...")
        result = subprocess.run(
            [str(python_bin), str(MANAGE_PY), 'collectstatic', '--noinput'],
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.warning(f"Failed to collect static: {result.stderr}")
        else:
            logger.info("Static files collected")
        
        # 5. Перезапуск сервисов
        logger.info("Restarting services...")
        result = subprocess.run(
            ['supervisorctl', 'restart', 'allitrader:*'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Failed to restart services: {result.stderr}")
            return False
        
        logger.info("Deployment completed successfully!")
        return True
        
    except Exception as e:
        logger.exception(f"Deploy failed with error: {e}")
        return False
