from django.shortcuts import render, redirect
from esi.decorators import token_required

from authenticated.decorators import app_access_required
from trader.apps import TraderConfig
from trader.scopes_for_traders import SCOPES_FOR_TRADERS
from trader.tasks import get_personage_assets
from EVE_Online_SQLite_API import get_stations_info
import logging

logger = logging.getLogger(__name__)


@app_access_required(TraderConfig.name)
def render_traders(request):
    return  render(request,'render_traders.html')

@app_access_required(TraderConfig.name)
@token_required(new=True, scopes=SCOPES_FOR_TRADERS)
def get_token_assets(request, token):
    assets_status = get_personage_assets.delay(token.id)
    return redirect('trader:render_traders')


def parser_assets(assets, character):
    """
    Парсер активов для сохранения в модель Asset
    Обновляет существующие активы, удаляет устаревшие и добавляет новые
    
    Args:
        assets: Список данных активов из API
        character: Объект EveCharacter, которому принадлежат активы
    """
    from trader.models import Asset, EveItemType, EveLocation
    
    # Получаем текущие item_id активов из API
    current_item_ids = set()
    
    # Собираем все уникальные ID станций
    station_ids = set()
    for item in assets:
        if item['location_type'] == 'station':
            station_ids.add(item['location_id'])

    #Batch-запрос информации о станциях
    stations_data = get_stations_info(list(station_ids))
    
    for item in assets:
        # Получаем данные станции, если location_type = station
        location_name = f"Location {item['location_id']}"
        if item['location_type'] == 'station':
            station_data = stations_data.get(item['location_id'])
            if station_data:
                location_name = station_data.get('stationName', f"Location {item['location_id']}")
            else:
                logger.warning(f"Не удалось получить данные для станции ID {item['location_id']}")
        # Создаем или получаем тип предмета
        item_type, _ = EveItemType.objects.get_or_create(
            type_id=item['type_id'],
            defaults={'type_name': f"Type {item['type_id']}"}
        )
        
        # Создаем или обновляем локацию (чтобы обновлялось имя станции)
        location, _ = EveLocation.objects.update_or_create(
            location_id=item['location_id'],
            defaults={
                'location_name': location_name,
                'location_type': item['location_type']
            }
        )
        
        # Создаем или обновляем актив
        asset, created = Asset.objects.update_or_create(
            item_id=item['item_id'],
            defaults={
                'is_singleton': item['is_singleton'],
                'location_flag': item['location_flag'],
                'location_id': item['location_id'],
                'location_type': item['location_type'],
                'quantity': item['quantity'],
                'type_id': item['type_id'],
                'character': character,
            }
        )
        
        current_item_ids.add(item['item_id'])
    
    # Удаляем активы, которые больше не пришли из API (кончились или переместились)
    Asset.objects.filter(character=character).exclude(item_id__in=current_item_ids).delete()
    
    return Asset.objects.filter(character=character).count()
