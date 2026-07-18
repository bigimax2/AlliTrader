import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.apps import apps

from core.app_task import app_task
from . import regions_systems_ids
from .views import prices_parser

logger = logging.getLogger(__name__)


@app_task
def get_prices():
    from .models import TypeSearchResult
    eveonline_config = apps.get_app_config('eveonline')
    esi = eveonline_config.esi
    type_search = TypeSearchResult.objects.all()
    regions = [
        regions_systems_ids.DOMAIN,
        regions_systems_ids.METROPOLIS,
        regions_systems_ids.THE_FORGE,
        regions_systems_ids.SING_LAISON,
        regions_systems_ids.HEIMATAR,
    ]
    hubs = [
        regions_systems_ids.JITA_HUB,
        regions_systems_ids.HEK_HUB,
        regions_systems_ids.AMARR_HUB,
        regions_systems_ids.DODIXIE_HUB,
        regions_systems_ids.RENS_HUB,
    ]
    price_results = []
    for region in regions:
        for type_item in type_search:
            try:
                if region == regions_systems_ids.THE_FORGE:
                    response = esi.client.Market.GetMarketsRegionIdOrders(region_id=region, order_type='buy', type_id=type_item.type_id)
                else:
                    response = esi.client.Market.GetMarketsRegionIdOrders(region_id=region, order_type='sell', type_id=type_item.type_id)
                result = response.results(force_refresh=True)
                price_results.append((region, result, None))
            except Exception as e:
                price_results.append((region, None, str(e)))
    
    # Фильтруем заказы по каждому хабу
    jita_orders = []
    hek_orders = []
    amarr_orders = []
    dodixie_orders = []
    rens_orders = []
    
    # Преобразуем hubs в set для быстрого поиска (как int)
    hub_ids = {int(hub) for hub in hubs}
    
    for region, result, error in price_results:
        if error or not result:
            continue
        for order in result:
            location_id = int(order.location_id) if hasattr(order, 'location_id') else None
            if location_id in hub_ids:
                if location_id == int(regions_systems_ids.JITA_HUB):
                    jita_orders.append(order)
                elif location_id == int(regions_systems_ids.HEK_HUB):
                    hek_orders.append(order)
                elif location_id == int(regions_systems_ids.AMARR_HUB):
                    amarr_orders.append(order)
                elif location_id == int(regions_systems_ids.DODIXIE_HUB):
                    dodixie_orders.append(order)
                elif location_id == int(regions_systems_ids.RENS_HUB):
                    rens_orders.append(order)
    
    # Преобразуем списки в кортежи
    jita_orders = tuple(jita_orders)
    hek_orders = tuple(hek_orders)
    amarr_orders = tuple(amarr_orders)
    dodixie_orders = tuple(dodixie_orders)
    rens_orders = tuple(rens_orders)
    
    # Отладка
    logger.info(f"JITA orders count: {len(jita_orders)}")
    logger.info(f"HEK orders count: {len(hek_orders)}")
    logger.info(f"Amarr orders count: {len(amarr_orders)}")
    logger.info(f"Dodixie orders count: {len(dodixie_orders)}")
    logger.info(f"Rens orders count: {len(rens_orders)}")
    
    # Подготовка данных для prices_parser с хабами
    hub_price_results = {
        'price_results': price_results,
        'jita_orders': jita_orders,
        'hek_orders': hek_orders,
        'amarr_orders': amarr_orders,
        'dodixie_orders': dodixie_orders,
        'rens_orders': rens_orders,
    }
    
    itog = prices_parser(hub_price_results)
    return itog
