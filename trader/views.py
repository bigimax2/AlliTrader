from django.shortcuts import render, redirect
from trader.forms import LocationSelectForm
from esi.decorators import token_required

from authenticated.decorators import app_access_required
from trader.apps import TraderConfig
from trader.scopes_for_traders import SCOPES_FOR_TRADERS
from trader.tasks import get_personage_assets
from EVE_Online_SQLite_API import get_stations_info, get_types_info
import logging

logger = logging.getLogger(__name__)


@app_access_required(TraderConfig.name)
def render_traders(request):
    if request.method == 'POST':
        form = LocationSelectForm(request.POST)
        locations_selected = []
        assets = []
        
        if form.is_valid():
            form.save()
            locations_selected = form.cleaned_data.get('locations', [])
            
            if locations_selected:
                # Получаем ID выбранных локаций
                location_ids = [loc.location_id for loc in locations_selected]
                location_flag = form.cleaned_data.get('location_flag', '')
                
                # Получаем ассеты для выбранных локаций
                from trader.models import Asset
                assets = Asset.objects.filter(
                    location__location_id__in=location_ids
                )
                
                # Фильтруем по location_flag, если указаны
                location_flags = form.cleaned_data.get('location_flag', [])
                if location_flags and '' not in location_flags:
                    assets = assets.filter(location_flag__in=location_flags)
                
                # Фильтруем по is_singleton, если указан
                is_singleton = form.cleaned_data.get('is_singleton', '')
                if is_singleton:
                    if is_singleton == '1':
                        assets = assets.filter(is_singleton=True)
                    else:
                        assets = assets.filter(is_singleton=False)
                
                assets = assets.select_related('character', 'type_id', 'location').order_by('location__location_id', 'type_id')
                
                logger.info(f"Выбрано локаций: {len(locations_selected)}, ID: {location_ids}")
                logger.info(f"Найдено ассетов: {assets.count()}")
        else:
            logger.error(f"Форма не валидна: {form.errors}")
    else:
        form = LocationSelectForm()
        locations_selected = []
        assets = []
    
    return render(request, 'render_traders.html', {
        'form': form,
        'locations_selected': locations_selected,
        'assets': assets
    })

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

    type_ids = set()
    # Собираем все уникальные ID станций
    station_ids = set()
    for item in assets:
        if item['location_type'] == 'station':
            station_ids.add(item['location_id'])
        type_ids.add(item['type_id'])
    type_data = get_types_info(list(type_ids))
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
        type_name = type_data.get(item['type_id'], {}).get('typeName', f"Type {item['type_id']}")
        item_type, _ = EveItemType.objects.update_or_create(
            type_id=item['type_id'],
            defaults={'type_name': type_name}
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
                'location': location,  # Связь с локацией
                'quantity': item['quantity'],
                'type_id': item_type,  # Передаем объект EveItemType, а не ID
                'character': character,
            }
        )
        
        current_item_ids.add(item['item_id'])
    
    # Удаляем активы, которые больше не пришли из API (кончились или переместились)
    Asset.objects.filter(character=character).exclude(item_id__in=current_item_ids).delete()
    
    return Asset.objects.filter(character=character).count()
