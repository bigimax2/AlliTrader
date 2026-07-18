from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from EVE_Online_SQLite_API import get_types_names
from authenticated.decorators import app_access_required
from eveonline.models import EveCharacter
from traders import regions_systems_ids
from traders.apps import TradersConfig
from traders.forms import TypeNamesForm
from traders.models import TypeSearchResult, PricesAssetsMarket


@app_access_required(TradersConfig.name)
@login_required
@require_http_methods(["POST"])
def delete_selected_type_search_results(request):
    """Удаление связи с персонажем для выбранных предметов (не удаляя сами предметы)"""
    try:
        type_ids = request.POST.getlist('selected_items[]')

        if not type_ids:
            messages.warning(request, 'Не выбрано ни одного элемента для удаления')
            return redirect('traders:type_names_lookup')

        # Получаем ID персонажа пользователя
        try:
            personage = request.user.userprofile.main_character_id
        except AttributeError:
            personage = None

        if personage is None:
            messages.error(request, 'Не найден основной персонаж пользователя')
            return redirect('traders:type_names_lookup')

        # Получаем объект персонажа
        try:
            character = EveCharacter.objects.get(character_id=personage)
        except EveCharacter.DoesNotExist:
            messages.error(request, 'Персонаж не найден в базе данных')
            return redirect('traders:type_names_lookup')

        # Удаляем только связь с персонажем для выбранных предметов
        deleted_count = 0
        for type_id in type_ids:
            try:
                type_result = TypeSearchResult.objects.get(type_id=type_id)
                type_result.character.remove(character)
                deleted_count += 1
            except TypeSearchResult.DoesNotExist:
                continue

        messages.success(request, f'Удалено {deleted_count} связей с персонажем')

    except Exception as e:
        messages.error(request, f'Ошибка удаления: {e}')

    return redirect('traders:type_names_lookup')

@app_access_required(TradersConfig.name)
@login_required
def type_names_lookup(request):
    """Представление для поиска информации о предметах по их именам"""
    type_names_save = None
    result_data = {}
    grouped_data = []
    accordion_data = {}  # Данные для аккордеона: категория -> список итемов

    try:
        personage = request.user.userprofile.main_character_id
    except AttributeError:
        personage = None

    if personage is None:
        return render(request, 'type_names_lookup.html', {
            'form': TypeNamesForm(),
            'result_data': result_data,
            'grouped_data': grouped_data,
            'accordion_data': accordion_data,
        })

    if request.method == 'POST':
        form = TypeNamesForm(request.POST)
        if form.is_valid():
            type_names_input = form.cleaned_data.get('type_names', '')
            # Разбиваем ввод на список имен (по одной на строку)
            type_names_list = [name.strip() for name in type_names_input.split('\n') if name.strip()]

            if type_names_list:
                result_data = get_types_names(type_names_list)
                # Парсим и сохраняем результаты в модель
                if result_data:
                    parse_and_save_type_search_results(result_data, personage)
                    # Подготовка данных для аккордеона
                    for type_id, type_info in result_data.items():
                        category_name = type_info.get('categoryName', 'Без категории')
                        if category_name not in accordion_data:
                            accordion_data[category_name] = []
                        accordion_data[category_name].append({
                            'type_id': type_id,
                            'groupName': type_info.get('groupName', ''),
                            'typeName': type_info.get('typeName', ''),
                        })
        else:
            form = TypeNamesForm()
    else:
        form = TypeNamesForm()
        type_names_save = TypeSearchResult.objects.filter(character__character_id=personage)
        for type_name in type_names_save:
            result_data[type_name.type_id] = {

                'categoryID': type_name.category_id,
                'categoryName': type_name.category_name,
                'groupID': type_name.group_id,
                'groupName': type_name.group_name,
                'typeName': type_name.type_name,
            }
            grouped_data.append({
                'type_id': type_name.type_id,
                'categoryName': type_name.category_name,
                'groupName': type_name.group_name,
                'typeName': type_name.type_name,
            })
            # Подготовка данных для аккордеона
            category_name = type_name.category_name or 'Без категории'
            if category_name not in accordion_data:
                accordion_data[category_name] = []
            accordion_data[category_name].append({
                'type_id': type_name.type_id,
                'groupName': type_name.group_name,
                'typeName': type_name.type_name,
            })

    return render(request, 'type_names_lookup.html', {
        'type_names_save': type_names_save,
        'form': form,
        'result_data': result_data,
        'grouped_data': grouped_data,
        'accordion_data': accordion_data,
    })

def parse_and_save_type_search_results(type_data, personage):
    """Функция для парсинга данных и сохранения их в модель TypeSearchResult"""
    if not type_data:
        return
    try:
        pers = EveCharacter.objects.get(character_id=personage)
    except EveCharacter.DoesNotExist:
        return
    for type_id, type_info in type_data.items():
        # Извлекаем данные из словаря
        type_name = type_info.get('typeName', '')
        group_id = type_info.get('groupID')
        group_name = type_info.get('groupName', '')
        category_id = type_info.get('categoryID')
        category_name = type_info.get('categoryName', '')

        # Создаем или обновляем запись в базе данных
        obj, created = TypeSearchResult.objects.get_or_create(
            type_id=type_id,
            defaults={
                'type_name': type_name,
                'group_id': group_id,
                'group_name': group_name,
                'category_id': category_id,
                'category_name': category_name,
            }
        )
        if created:
            obj.character.add(pers)
        elif pers not in obj.character.all():
            obj.character.add(pers)

def prices_parser(hub_price_results):
    """Parses price results and returns processed data only for hubs.
    
    Args:
        hub_price_results: dict with:
            - 'price_results': list of tuples (region, result, error)
            - 'jita_orders', 'hek_orders', etc.: tuples of orders filtered by hub
    
    Returns:
        dict: processed price data with hub orders only
    """
    parsed_data = {}
    
    # Добавляем данные по хабам
    hub_order_names = ['jita_orders', 'hek_orders', 'amarr_orders', 'dodixie_orders', 'rens_orders']
    hub_regions = {
        'jita_orders': regions_systems_ids.JITA_HUB,
        'hek_orders': regions_systems_ids.HEK_HUB,
        'amarr_orders': regions_systems_ids.AMARR_HUB,
        'dodixie_orders': regions_systems_ids.DODIXIE_HUB,
        'rens_orders': regions_systems_ids.RENS_HUB,
    }
    
    for hub_name in hub_order_names:
        hub_orders = hub_price_results.get(hub_name, [])
        hub_region_id = hub_regions[hub_name]
        
        # Фильтруем по цене
        filtered_orders = filter_orders_by_price(hub_orders, hub_name)
        
        parsed_data[hub_region_id] = {
            'error': None,
            'orders': filtered_orders
        }
    res = update_prises(parsed_data)
    return res

def filter_orders_by_price(orders, hub_name):
    """Filter orders by price based on hub type, grouped by type_id.
    
    For JITA (buy orders): for each type_id, return orders with max price
    For other hubs (sell orders): for each type_id, return orders with min price
    
    Args:
        orders: list of order objects
        hub_name: name of the hub (jita_orders, hek_orders, etc.)
    
    Returns:
        list: filtered orders (one per type_id with max/min price)
    """
    if not orders:
        return []
    
    is_jita = 'jita' in hub_name.lower()
    
    # Группируем заказы по type_id
    orders_by_type = {}
    for order in orders:
        type_id = order.type_id
        if type_id not in orders_by_type:
            orders_by_type[type_id] = []
        orders_by_type[type_id].append(order)
    
    filtered_orders = []
    
    if is_jita:
        # Для JITA - для каждого type_id выбираем максимальную цену
        for type_id, type_orders in orders_by_type.items():
            max_price = max(order.price for order in type_orders)
            filtered_orders.extend([order for order in type_orders if order.price == max_price])
    else:
        # Для других хабов - для каждого type_id выбираем минимальную цену
        for type_id, type_orders in orders_by_type.items():
            min_price = min(order.price for order in type_orders)
            filtered_orders.extend([order for order in type_orders if order.price == min_price])
    
    return filtered_orders

def update_prises(parsed_data):
    """Обновляет цены в базе данных для каждого хаба.
    
    Args:
        parsed_data: dict с отфильтрованными заказами по хабам
    
    Returns:
        bool: True при успешном обновлении
    """
    # Словарь сопоставления хабов и полей модели
    hub_field_map = {
        regions_systems_ids.JITA_HUB: 'maxbuyjita',
        regions_systems_ids.HEK_HUB: 'minsellhek',
        regions_systems_ids.AMARR_HUB: 'minsellamarr',
        regions_systems_ids.DODIXIE_HUB: 'minselldodixie',
        regions_systems_ids.RENS_HUB: 'minsellrens',
    }
    
    # Собираем все обновления в одном цикле
    for p_data, field_name in hub_field_map.items():
        if p_data in parsed_data and parsed_data[p_data]['orders']:
            orders = parsed_data[p_data]['orders']
            for order in orders:
                PricesAssetsMarket.objects.update_or_create(
                    type_id=order.type_id,
                    defaults={field_name: order.price}
                )
    
    return True