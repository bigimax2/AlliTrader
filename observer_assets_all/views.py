from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from esi.models import Token

from authenticated.decorators import app_access_required
from eveonline.models import EveCharacter
from observer_assets_all.apps import ObserverAssetsAllConfig
from observer_assets_all.assets_forms import AssetsOverviewForm, TypeNamesForm
import logging

logger = logging.getLogger(__name__)

from EVE_Online_SQLite_API import get_types_names
from observer_assets_all.scopes_for_traders import SCOPES_FOR_TRADERS
from observer_assets_single.models import EveLocation, EveItemType, AlertThreshold, Asset
from observer_assets_all.models import TypeSearchResult


def build_location_hierarchy(assets, character, alert_thresholds):
    """
    Построение иерархии ассетов внутри локации для отображения с аккордеоном.

    Ассеты на открытом пространстве локации отображаются отдельно.
    Ассеты внутри контейнеров группируются по контейнерам в аккордеоне.

    Args:
        assets: queryset ассетов для одной локации
        character: Объект EveCharacter
        alert_thresholds: словарь {type_id: min_quantity} для алертов

    Returns:
        Словарь с двумя ключами:
        - 'open_assets': список ассетов на открытом пространстве
        - 'container_groups': словарь {item_id: {'name': ..., 'assets': [...]}}
    """
    from observer_assets_single.models import Asset

    if not assets:
        return {'open_assets': [], 'container_groups': {}}

    # Получаем item_id всех ассетов в текущей локации
    location_item_ids = [asset.item_id for asset in assets]

    # Собираем все ID контейнеров/кораблей, в которых могут быть ассеты
    # Это включает как ассеты на открытом пространстве, так и все вложенные контейнеры
    all_container_ids = set()

    # Сначала находим все контейнеры (is_singleton=True) среди переданных ассетов
    for asset in assets:
        if asset.is_singleton:
            all_container_ids.add(asset.item_id)

    # Находим все ассеты, которые находятся внутри любых контейнеров
    # Ищем по location.location_id (контейнеры на верхнем уровне) и parent_item_id (вложенные ассеты)
    container_contents = Asset.objects.filter(
        character=character,
        location__location_id__in=location_item_ids
    ).select_related('location', 'type_id').distinct()

    # Добавляем вложенные контейнеры в список
    nested_container_ids = set()
    for content in container_contents:
        if content.is_singleton:
            nested_container_ids.add(content.item_id)

    # Если есть вложенные контейнеры, ищем ассеты внутри них рекурсивно
    while nested_container_ids:
        nested_contents = Asset.objects.filter(
            character=character,
            location__location_id__in=nested_container_ids
        ).select_related('location', 'type_id').distinct()

        # Добавляем найденные ассеты в container_contents
        existing_ids = {c.item_id for c in container_contents}
        for content in nested_contents:
            if content.item_id not in existing_ids:
                container_contents = list(container_contents) + [content]
                if content.is_singleton:
                    nested_container_ids.add(content.item_id)

        # Обновляем список для следующей итерации
        nested_container_ids = {c.item_id for c in nested_contents if c.is_singleton and c.item_id not in existing_ids}

    # Группируем ассеты
    open_assets = []
    container_groups = {}  # {item_id: {'name': ..., 'assets': [...]}}

    # Сначала собираем ассеты, которые находятся внутри контейнеров
    container_assets_map = {}  # {item_id: [assets inside]}
    for content in container_contents:
        loc_id = content.location.location_id
        if loc_id not in container_assets_map:
            container_assets_map[loc_id] = []
        container_assets_map[loc_id].append(content)
        logger.info(
            f"Container content: item_id={content.item_id}, type_id={content.type_id.type_id}, location.location_id={loc_id}, is_singleton={content.is_singleton}")

    # Копируем атрибут alert_level из исходных ассетов в ассеты из container_contents
    # Это нужно, потому что container_contents - это новые объекты из БД без alert_level
    logger.info(f"Kopirovka alert_level: container_assets_map keys={list(container_assets_map.keys())}")

    # Для каждого ассета внутри контейнера вычисляем alert_level заново по его количеству
    for item_id, assets_list in container_assets_map.items():
        for asset in assets_list:
            type_id = asset.type_id.type_id
            qty = int(asset.quantity)

            # Ищем порог для этого type_id
            threshold = alert_thresholds.get(type_id)
            if threshold is not None:
                thresh = int(threshold)
                critical_threshold = thresh * 0.25
                warning_threshold = thresh * 0.5

                if qty <= critical_threshold:
                    asset.alert_level = 'critical'
                    logger.info(
                        f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=critical")
                elif qty <= warning_threshold:
                    asset.alert_level = 'warning'
                    logger.info(
                        f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=warning")
                elif qty == thresh:
                    asset.alert_level = 'warning'
                    logger.info(
                        f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=warning (equal to threshold)")
                else:
                    asset.alert_level = None
                    logger.info(
                        f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=None")
            else:
                asset.alert_level = None
                logger.info(
                    f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, no threshold found")

    # Затем обрабатываем исходные ассеты
    for asset in assets:
        item_id = asset.item_id
        category_name = asset.type_id.category_name if asset.type_id else None

        # Проверяем, есть ли ассеты внутри этого предмета
        if item_id in container_assets_map:
            # Это контейнер/ship - добавляем в container_groups
            # Имя берем от самого объекта контейнера/ship из assets
            container_name = asset.type_id.type_name if asset.type_id else f"Контейнер {item_id}"

            container_groups[item_id] = {
                'name': container_name,
                'assets': container_assets_map[item_id],
                'category_name': category_name
            }
            logger.info(f"Found container: item_id={item_id}, name={container_name}, category_name={category_name}")
            # Логируем ассеты внутри контейнера
            for container_asset in container_assets_map[item_id]:
                logger.info(
                    f"  Container asset: item_id={container_asset.item_id}, type_id={container_asset.type_id.type_id}, quantity={container_asset.quantity}, alert_level={getattr(container_asset, 'alert_level', 'NOT SET')}")
        else:
            # Это ассет на открытом пространстве
            open_assets.append(asset)
            logger.info(
                f"Open asset: item_id={item_id}, type_id={asset.type_id.type_id}, category_name={category_name}, alert_level={getattr(asset, 'alert_level', 'NOT SET')}")

    return {'open_assets': open_assets, 'container_groups': container_groups}


@app_access_required(ObserverAssetsAllConfig.name)
@login_required
def assets_overview(request):
    # Проверяем, есть ли у пользователя хотя бы один токен с нужными scopes
    has_valid_token = Token.objects.filter(
        user=request.user,
        scopes__name__in=SCOPES_FOR_TRADERS
    ).exists()

    if request.method == 'POST':
        form = AssetsOverviewForm(request.POST, user=request.user)
        locations_selected = []
        assets = []

        # Сохраняем состояние чекбокса в session
        show_chized_ships_value = form.data.get('show_chized_ships')
        if show_chized_ships_value:
            request.session['show_chized_ships'] = True
        else:
            request.session['show_chized_ships'] = False

        if form.is_valid():
            form.save()
            locations_selected = form.cleaned_data.get('locations', [])

            if locations_selected:
                # Получаем ID выбранных локаций
                location_ids = [loc.location_id for loc in locations_selected]
                location_flag = form.cleaned_data.get('location_flag', '')

                # Получаем ассеты для выбранных локаций
                from observer_assets_single.models import Asset
                # Получаем выбранных персонажей или всех персонажей с токенами доступа к ассетам
                selected_characters = form.cleaned_data.get('character', [])
                if selected_characters:
                    character_ids = selected_characters
                else:
                    # Получаем все character_id с токенами, имеющими доступ к ассетам
                    character_ids = Token.objects.filter(
                        scopes__name__in=SCOPES_FOR_TRADERS
                    ).values_list('character_id', flat=True).distinct()

                assets = Asset.objects.filter(
                    character__character_id__in=character_ids,
                    location__location_id__in=location_ids
                ).select_related('character', 'type_id', 'location')

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

                # Фильтруем по category_name, если указан (множественный выбор)
                category_names = form.cleaned_data.get('category_name', [])
                if category_names and '' not in category_names:
                    assets = assets.filter(type_id__category_name__in=category_names)

                # Загружаем пороги алертов для текущего пользователя
                user_id = request.user.id if request.user.is_authenticated else 0
                from observer_assets_single.models import AlertThreshold
                alert_thresholds = {at.type_id_id: at.min_quantity for at in
                                    AlertThreshold.objects.filter(user_id=user_id)}

                logger.info(f"User ID: {user_id}, Порогов алертов: {len(alert_thresholds)}")
                logger.info(f"Пороги: {alert_thresholds}")

                # Фильтруем по alert_level после вычисления для всех ассетов (включая контейнеры)
                # Для этого сначала строим иерархию, потом фильтруем по alert_level
                alert_level_filter = form.cleaned_data.get('alert_level', '')

                assets = assets.order_by('character__name', 'location__location_id', 'type_id')

                # Загружаем пороги алертов для текущего пользователя
                user_id = request.user.id if request.user.is_authenticated else 0
                from observer_assets_single.models import AlertThreshold
                alert_thresholds = {at.type_id_id: at.min_quantity for at in
                                    AlertThreshold.objects.filter(user_id=user_id)}

                logger.info(f"User ID: {user_id}, Порогов алертов: {len(alert_thresholds)}")
                logger.info(f"Пороги: {alert_thresholds}")

                # Добавляем информацию о низком количестве
                for asset in assets:
                    # Используем asset.type_id.type_id, так как type_id - это ForeignKey объект
                    threshold = alert_thresholds.get(asset.type_id.type_id)
                    if threshold is not None:
                        qty = int(asset.quantity)
                        thresh = int(threshold)
                        # critical: qty <= thresh + 15% от thresh (порог + 15%)
                        # warning: qty <= thresh + 30% от thresh (порог + 30%)
                        critical_threshold = thresh * 0.25
                        warning_threshold = thresh * 0.5
                        logger.info(f"Asset type_id={asset.type_id.type_id}, quantity={qty}, threshold={thresh}")
                        logger.info(f"  thresholds: critical={critical_threshold}, warning={warning_threshold}")

                        if qty <= critical_threshold:
                            asset.alert_level = 'critical'
                            logger.info(f"  -> critical (qty={qty} <= {critical_threshold})")
                        elif qty <= warning_threshold:
                            asset.alert_level = 'warning'
                            logger.info(f"  -> warning (qty={qty} <= {warning_threshold})")
                        elif qty == thresh:
                            asset.alert_level = 'warning'
                            logger.info(f"  -> warning (qty={qty} = {thresh})")
                        else:
                            asset.alert_level = None
                            logger.info(f"  -> None (qty={qty} > {warning_threshold})")
                    else:
                        asset.alert_level = None
                        logger.info(
                            f"Asset type_id={asset.type_id.type_id}, quantity={asset.quantity}, no threshold found")

                logger.info(f"Выбрано локаций: {len(locations_selected)}, ID: {location_ids}")
                logger.info(f"Найдено ассетов: {assets.count()}")

                # Группируем ассеты по локациям для отображения с аккордеоном
                from collections import defaultdict
                assets_by_location = defaultdict(list)
                for asset in assets:
                    location_obj = asset.location if asset.location else None
                    if location_obj:
                        assets_by_location[location_obj].append(asset)

                # Строим иерархию для каждой локации
                location_data = {}
                for location_obj, loc_assets in assets_by_location.items():
                    # Получаем всех уникальных персонажей для этой локации
                    unique_characters = set(asset.character for asset in loc_assets if asset.character)
                    if len(unique_characters) == 1:
                        character = unique_characters.pop()
                    else:
                        # Если несколько персонажей, берем первого
                        character = loc_assets[0].character if loc_assets[0].character else None

                    location_data[location_obj.location_id] = build_location_hierarchy(loc_assets, character,
                                                                                       alert_thresholds)

                logger.info(f"Строено иерархий для локаций: {len(location_data)}")

                # Фильтруем по alert_level после построения иерархии
                alert_level_filter = form.cleaned_data.get('alert_level', '')
                if alert_level_filter and location_data:
                    for location_id, loc_hierarchy in location_data.items():
                        # Фильтруем open_assets
                        if 'open_assets' in loc_hierarchy:
                            loc_hierarchy['open_assets'] = [
                                asset for asset in loc_hierarchy['open_assets']
                                if getattr(asset, 'alert_level', None) == alert_level_filter
                            ]
                        
                        # Фильтруем container_groups по ассетам внутри
                        if 'container_groups' in loc_hierarchy:
                            filtered_container_groups = {}
                            for item_id, container_data in loc_hierarchy['container_groups'].items():
                                filtered_assets = [
                                    asset for asset in container_data['assets']
                                    if getattr(asset, 'alert_level', None) == alert_level_filter
                                ]
                                if filtered_assets:
                                    filtered_container_groups[item_id] = {
                                        'name': container_data['name'],
                                        'assets': filtered_assets,
                                        'category_name': container_data.get('category_name')
                                    }
                            loc_hierarchy['container_groups'] = filtered_container_groups

                logger.info(f"Фильтрация по alert_level завершена")

                # Фильтруем зафиченные шипы из container_groups, если не выбрано показывать
                show_chized_ships = form.cleaned_data.get('show_chized_ships', False)
                if not show_chized_ships:
                    for location_id, loc_hierarchy in location_data.items():
                        if 'container_groups' in loc_hierarchy:
                            # Удаляем контейнеры, которые являются зафиченными шипами
                            # зафиченный шип: category_name='Ship'
                            items_to_remove = []
                            for item_id, container_data in loc_hierarchy['container_groups'].items():
                                # Ищем исходный ассет для получения category_name и location_flag
                                container_asset = next(
                                    (a for a in assets if a.item_id == item_id),
                                    None
                                )
                                if container_asset and container_asset.type_id:
                                    category_name = container_asset.type_id.category_name
                                    location_flag = container_asset.location_flag

                                    # Удаляем только если оба условия выполнены
                                    if category_name == 'Ship':
                                        items_to_remove.append(item_id)
                                        logger.info(
                                            f"Удален зафиченный шип из контейнеров: item_id={item_id}, category_name={category_name}, location_flag={location_flag}")

                            for item_id in items_to_remove:
                                del loc_hierarchy['container_groups'][item_id]

                logger.info(f"Фильтрация container_groups завершена")
        else:
            logger.error(f"Форма не валидна: {form.errors}")
    else:
        # GET request - read from session storage
        show_chized_ships_value = request.session.get('show_chized_ships', False)

        initial_data = {
            'show_chized_ships': show_chized_ships_value
        }

        form = AssetsOverviewForm(user=request.user, initial=initial_data)
        locations_selected = []
        assets = []

    return render(request, 'assets_overview.html', {
        'form': form,
        'locations_selected': locations_selected,
        'assets': assets,
        'location_data': location_data if locations_selected else {},
        'alert_thresholds': alert_thresholds if locations_selected else {},
        'user_characters': EveCharacter.objects.filter(assets__isnull=False).distinct().order_by('name') if request.user.is_authenticated else [],
        'has_valid_token': has_valid_token if request.user.is_authenticated else False
    })


@app_access_required(ObserverAssetsAllConfig.name)
@login_required
@require_http_methods(["POST"])
def delete_selected_type_search_results(request):
    """Массовое удаление записей из TypeSearchResult"""
    try:
        type_ids = request.POST.getlist('selected_items[]')
        
        if not type_ids:
            messages.warning(request, 'Не выбрано ни одного элемента для удаления')
            return redirect('observer_assets_all:type_names_lookup')
        
        # Получаем ID персонажа пользователя
        try:
            personage = request.user.userprofile.main_character_id
        except AttributeError:
            personage = None
        
        if personage is None:
            messages.error(request, 'Не найден основной персонаж пользователя')
            return redirect('observer_assets_all:type_names_lookup')
        
        # Удаляем только записи текущего пользователя
        deleted_count, _ = TypeSearchResult.objects.filter(
            type_id__in=type_ids,
            character__character_id=personage
        ).delete()
        
        messages.success(request, f'Удалено {deleted_count} предмет(ов) из списка')
        
    except Exception as e:
        messages.error(request, f'Ошибка удаления: {e}')
    
    return redirect('observer_assets_all:type_names_lookup')


@app_access_required(ObserverAssetsAllConfig.name)
@login_required
def type_names_lookup(request):
    """Представление для поиска информации о предметах по их именам"""
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
                    parse_and_save_type_search_results(result_data,personage)
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
        # Пытаемся использовать character__character_id, если поле существует
        # Если нет - используем character_id напрямую (старая версия таблицы)
        try:
            type_names_save = TypeSearchResult.objects.filter(character__character_id=personage)
        except Exception:
            type_names_save = TypeSearchResult.objects.filter(character_id=personage)
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
        TypeSearchResult.objects.update_or_create(
            type_id=type_id,
            defaults={
                'type_name': type_name,
                'group_id': group_id,
                'group_name': group_name,
                'category_id': category_id,
                'category_name': category_name,
                'character': pers,
            }
        )
