import logging

from django.apps import apps

from core.app_task import app_task
from trader.scopes_for_traders import SCOPES_FOR_TRADERS
from esi.exceptions import HTTPNotModified

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
