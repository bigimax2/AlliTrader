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


def add_alerts_to_assets(assets):
    """
    Добавляет поле alert_level к каждому ассету на основе порогов алертов.
    Алерты фильтруются по пользователям, чьи ассеты присутствуют в выборке.
    Также получает ассеты из контейнеров и добавляет к ним alert_level.
    
    Args:
        assets: queryset ассетов
    
    Returns:
        queryset ассетов с добавленным полем alert_level (включая ассеты из контейнеров)
    """
    if not assets.exists():
        return assets
    
    # Получаем unique user_id из выбранных персонажей
    user_ids = assets.values_list('character__ownership_records__user_id', flat=True).distinct()
    user_ids = [uid for uid in user_ids if uid is not None]
    
    if not user_ids:
        return assets
    
    # Получаем все алерты для этих пользователей
    # Словарь: {type_id: {user_id: min_quantity}}
    alert_thresholds = {}
    thresholds = AlertThreshold.objects.filter(user_id__in=user_ids).select_related('type_id')
    for threshold in thresholds:
        type_id = threshold.type_id_id
        user_id = threshold.user_id
        if type_id not in alert_thresholds:
            alert_thresholds[type_id] = {}
        alert_thresholds[type_id][user_id] = threshold.min_quantity
    
    # Получаем ID всех персонажей из текущей выборки
    character_ids = assets.values_list('character_id', flat=True).distinct()
    
    # Получаем ID всех локаций (станций), где находятся ассеты
    location_ids = assets.values_list('location_id', flat=True).distinct()
    
    # Получаем все ассеты на выбранных локациях (без фильтров)
    all_location_assets = Asset.objects.filter(
        character__character_id__in=character_ids,
        location_id__in=location_ids
    ).select_related('character', 'type_id', 'location')
    
    # Получаем контейнеры (is_singleton=True) из всех ассетов на локациях
    # Исключаем зафиченные шипы (category_name='Ship')
    container_assets = all_location_assets.filter(
        is_singleton=True
    ).exclude(type_id__category_name='Ship')
    
    # Получаем ID всех контейнеров
    container_ids = container_assets.values_list('item_id', flat=True).distinct()
    
    # Получаем ассеты из контейнеров для всех выбранных персонажей
    # Ассеты внутри контейнеров имеют location__location_id равный item_id контейнера
    container_contents = Asset.objects.filter(
        character__character_id__in=character_ids,
        location__location_id__in=container_ids
    ).exclude(id__in=assets.values_list('id', flat=True)).exclude(id__in=container_assets.values_list('id', flat=True)).select_related(
        'character', 'type_id', 'location'
    ).distinct()
    
    # Получаем ID всех контейнеров, чтобы найти вложенные контейнеры
    nested_container_ids = set(container_assets.values_list('item_id', flat=True))
    
    # Рекурсивно получаем ассеты из вложенных контейнеров
    while nested_container_ids:
        # Получаем ассеты внутри текущих контейнеров (по location__location_id)
        nested_contents = Asset.objects.filter(
            character__character_id__in=character_ids,
            location__location_id__in=nested_container_ids
        ).exclude(id__in=assets.values_list('id', flat=True)).exclude(id__in=container_contents.values_list('id', flat=True)).exclude(id__in=container_assets.values_list('id', flat=True)).select_related(
            'character', 'type_id', 'location'
        ).distinct()
        
        if not nested_contents:
            break
        
        # Добавляем найденные ассеты в container_contents
        container_contents = list(container_contents) + list(nested_contents)
        
        # Обновляем список контейнеров для следующей итерации
        nested_container_ids = {c.item_id for c in nested_contents if c.is_singleton}
    
    # Добавляем алерты для контейнерных ассетов
    for asset in container_contents:
        type_id = asset.type_id_id
        user_id = None
        
        # Получаем user_id через character
        if asset.character and hasattr(asset.character, 'ownership_records'):
            user_record = asset.character.ownership_records.first()
            if user_record:
                user_id = user_record.user_id
        
        # Ищем порог для этого type_id и user_id
        threshold = None
        if type_id in alert_thresholds:
            if user_id and user_id in alert_thresholds[type_id]:
                threshold = alert_thresholds[type_id][user_id]
            else:
                # Если для конкретного пользователя нет порога, берем любой доступный
                for uid, qty in alert_thresholds[type_id].items():
                    threshold = qty
                    break
        
        # Вычисляем alert_level
        if threshold is not None:
            qty = int(asset.quantity)
            thresh = int(threshold)
            asset.alert_threshold = thresh  # Добавляем порог алерта
            critical_threshold = thresh * 0.25
            warning_threshold = thresh * 0.5
            
            if qty <= critical_threshold:
                asset.alert_level = 'critical'
            elif qty <= warning_threshold:
                asset.alert_level = 'warning'
            elif qty == thresh:
                asset.alert_level = 'warning'
            else:
                asset.alert_level = None
        else:
            asset.alert_level = None
            asset.alert_threshold = None
    
    # Добавляем алерты к исходным ассетам
    for asset in assets:
        type_id = asset.type_id_id
        user_id = None
        
        # Получаем user_id через character
        if asset.character and hasattr(asset.character, 'ownership_records'):
            user_record = asset.character.ownership_records.first()
            if user_record:
                user_id = user_record.user_id
        
        # Ищем порог для этого type_id и user_id
        threshold = None
        if type_id in alert_thresholds:
            if user_id and user_id in alert_thresholds[type_id]:
                threshold = alert_thresholds[type_id][user_id]
            else:
                # Если для конкретного пользователя нет порога, берем любой доступный
                for uid, qty in alert_thresholds[type_id].items():
                    threshold = qty
                    break
        
        # Вычисляем alert_level
        if threshold is not None:
            qty = int(asset.quantity)
            thresh = int(threshold)
            asset.alert_threshold = thresh  # Добавляем порог алерта
            critical_threshold = thresh * 0.25
            warning_threshold = thresh * 0.5
            
            if qty <= critical_threshold:
                asset.alert_level = 'critical'
            elif qty <= warning_threshold:
                asset.alert_level = 'warning'
            elif qty == thresh:
                asset.alert_level = 'warning'
            else:
                asset.alert_level = None
        else:
            asset.alert_level = None
            asset.alert_threshold = None
    
    # Объединяем исходные ассеты и ассеты из контейнеров
    # Добавляем флаг is_container_asset для различия
    logger.info(f"add_alerts_to_assets: open_assets count={assets.count() if hasattr(assets, 'count') else len(assets)}")
    logger.info(f"add_alerts_to_assets: container_contents count={container_contents.count() if hasattr(container_contents, 'count') else len(container_contents)}")
    
    # Группируем контейнерные ассеты по персонажам
    from collections import defaultdict
    container_assets_by_character = defaultdict(list)
    
    for asset in container_contents:
        asset.is_container_asset = True
        # Получаем character_id для группировки
        char_id = asset.character.character_id if asset.character else None
        if char_id:
            container_assets_by_character[char_id].append(asset)
        logger.info(f"Container asset: item_id={asset.item_id}, type_id={asset.type_id_id}, quantity={asset.quantity}, location={asset.location.location_name}")
    
    # Возвращаем dict с двумя ключами
    return {
        'assets': list(assets),
        'container_assets_by_character': dict(container_assets_by_character)
    }


@app_access_required(ObserverAssetsAllConfig.name)
@login_required
def assets_overview(request):
    """Представление для отображения всех ассетов всех персонажей с токенами доступа"""
    from observer_assets_single.models import Asset

    # Проверяем, есть ли у пользователя хотя бы один токен с нужными scopes
    has_valid_token = Token.objects.filter(
        user=request.user,
        scopes__name__in=SCOPES_FOR_TRADERS
    ).exists()

    # Получаем всех персонажей с токенами доступа к ассетам
    characters_with_assets = EveCharacter.objects.filter(
        ownership_records__user=request.user
    ).order_by('name').distinct()

    # Получаем всех персонажей (для формы фильтрации)
    # Запрашиваем персонажей, у которых есть токен с доступом к ассетам
    all_characters = EveCharacter.objects.filter(
        ownership_records__user__isnull=False
    ).filter(
        character_id__in=Token.objects.filter(scopes__name__in=SCOPES_FOR_TRADERS).values_list('character_id',
                                                                                               flat=True)
    ).order_by('name').distinct()

    # Если нет персонажей с токенами, используем всех персонажей пользователя
    if not all_characters.exists():
        all_characters = characters_with_assets

    # Получаем все доступные локации
    all_locations = EveLocation.objects.filter(location_type='station').order_by('location_name')

    # Получаем все уникальные категории и группы для фильтрации
    all_categories = EveItemType.objects.exclude(category_name='').values_list('category_name',
                                                                               flat=True).distinct().order_by(
        'category_name')
    all_groups = EveItemType.objects.exclude(group_name='').values_list('group_name', flat=True).distinct().order_by(
        'group_name')

    assets = Asset.objects.all()

    if request.method == 'POST':
        form = AssetsOverviewForm(request.POST, user=request.user, all_locations=all_locations,
                                  all_categories=all_categories, all_groups=all_groups, user_characters=all_characters)
        if form.is_valid():
            character_ids = form.cleaned_data.get('character', [])
            location_ids = form.cleaned_data.get('locations', [])
            location_flags = form.cleaned_data.get('location_flag', [])
            is_singleton = form.cleaned_data.get('is_singleton', '')
            category_names = form.cleaned_data.get('category_name', [])
            group_names = form.cleaned_data.get('group_name', [])

            # Применяем фильтры
            # Фильтруем по персонажам (проверяем, не выбран ли 'Выбрать всех')
            if character_ids:
                # Если в списке есть '__all__', берем всех персонажей
                if '__all__' not in character_ids:
                    assets = assets.filter(character__character_id__in=character_ids)

            # Фильтруем по локациям (проверяем, не выбрана ли 'Выбрать все')
            if location_ids:
                # Если в списке есть '__all__', берем только локации типа station
                if '__all__' in location_ids:
                    assets = assets.filter(location__location_type='station')
                else:
                    assets = assets.filter(location__location_id__in=location_ids)
            else:
                # Если локации не выбраны, фильтруем по station по умолчанию
                assets = assets.filter(location__location_type='station')

            if location_flags and '' not in location_flags:
                assets = assets.filter(location_flag__in=location_flags)

            if is_singleton:
                if is_singleton == '1':
                    assets = assets.filter(is_singleton=True)
                else:
                    assets = assets.filter(is_singleton=False)

            if category_names and '' not in category_names:
                assets = assets.filter(type_id__category_name__in=category_names)

            if group_names and '' not in group_names:
                assets = assets.filter(type_id__group_name__in=group_names)

            assets = assets.select_related('character', 'type_id', 'location').order_by('character__name',
                                                                                        'location__location_name',
                                                                                        'type_id__type_name')
            
            # Добавляем алерты для выбранных персонажей (включая ассеты из контейнеров)
            logger.info(f"assets_overview: Выбрано {len(character_ids)} персонажей, {len(location_ids)} локаций")
            assets_result = add_alerts_to_assets(assets)
            
            # Извлекаем открытые ассеты и контейнеры по персонажам
            open_assets = assets_result['assets']
            container_assets_by_character = assets_result['container_assets_by_character']
            
            logger.info(f"assets_overview: open_assets={len(open_assets)}, container_assets_by_character keys={list(container_assets_by_character.keys())}")
            
            # Объединяем все контейнерные ассеты для отображения в отдельном блоке (если нужно)
            all_container_assets = []
            for char_id, char_assets in container_assets_by_character.items():
                all_container_assets.extend(char_assets)
                logger.info(f"char_id={char_id}, char_assets count={len(char_assets)}")
                for ca in char_assets:
                    logger.info(f"  Container: item_id={ca.item_id}, parent_item_id={ca.parent_item_id}, location={ca.location.location_name}")
            
            # Группируем контейнерные ассеты по локации для отображения
            from collections import defaultdict
            container_groups = defaultdict(list)
            for asset in all_container_assets:
                loc_name = asset.location.location_name or f"Контейнер {asset.location.location_id}"
                container_groups[loc_name].append(asset)
                logger.info(f"Container asset grouped: loc_name={loc_name}, item_id={asset.item_id}, type_id={asset.type_id_id}")
            
            logger.info(f"container_groups: {dict(container_groups)}")
            
            # Используем all_container_assets для отображения в шаблоне
            container_assets = all_container_assets
        else:
            open_assets = Asset.objects.none()
            container_assets = []
            container_groups = {}
            container_assets_by_character = {}
    else:
        form = AssetsOverviewForm(user=request.user, all_locations=all_locations, all_categories=all_categories,
                                  all_groups=all_groups, user_characters=all_characters)
        open_assets = Asset.objects.none()  # Не выгружаем ассеты при первом открытии
        container_assets = []
        container_groups = {}
        container_assets_by_character = {}
    
    # Считаем总 ассеты (для POST и GET запросов)
    total_open = len(open_assets) if hasattr(open_assets, '__len__') else (open_assets.count() if hasattr(open_assets, 'count') else 0)
    total_container = len(container_assets) if hasattr(container_assets, '__len__') else (container_assets.count() if hasattr(container_assets, 'count') else 0)
    total_assets = total_open + total_container

    return render(request, 'assets_overview.html', {
        'form': form,
        'open_assets': open_assets,
        'container_assets': container_assets,
        'container_groups': dict(container_groups),
        'container_assets_by_character': container_assets_by_character,
        'all_characters': all_characters,
        'user_characters': characters_with_assets,
        'all_locations': all_locations,
        'all_categories': all_categories,
        'all_groups': all_groups,
        'has_valid_token': has_valid_token if request.user.is_authenticated else False,
        'total_assets': total_assets,
        'total_characters': characters_with_assets.count(),
        'is_filtered': request.method == 'POST',  # Флаг применения фильтров
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
