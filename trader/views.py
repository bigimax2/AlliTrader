from django.shortcuts import render, redirect
from esi.decorators import token_required

from authenticated.decorators import app_access_required
from trader.apps import TraderConfig
from trader.scopes_for_traders import SCOPES_FOR_TRADERS
from trader.tasks import get_personage_assets


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
    
    Args:
        assets: Список данных активов из API
        character: Объект EveCharacter, которому принадлежат активы
    """
    from trader.models import Asset, EveItemType, EveLocation
    
    for item in assets:
        # Создаем или получаем тип предмета
        item_type, _ = EveItemType.objects.get_or_create(
            type_id=item['type_id'],
            defaults={'type_name': f"Type {item['type_id']}"}
        )
        
        # Создаем или получаем локацию
        location, _ = EveLocation.objects.get_or_create(
            location_id=item['location_id'],
            defaults={
                'location_name': f"Location {item['location_id']}",
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
    
    return Asset.objects.filter(character=character).count()