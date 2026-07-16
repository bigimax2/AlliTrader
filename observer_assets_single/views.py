from django.shortcuts import render, redirect
from django.db import models
from observer_assets_single.forms import LocationSelectForm, AlertThresholdForm
from esi.decorators import token_required

from authenticated.decorators import app_access_required
from observer_assets_single.apps import ObserverAssetsSingleConfig
from observer_assets_single.scopes_for_traders import SCOPES_FOR_TRADERS
from observer_assets_single.tasks import get_personage_assets
from EVE_Online_SQLite_API import get_stations_info, get_types_info
from django.contrib.auth.decorators import login_required
from observer_assets_single.models import EveItemType, AlertThreshold
from eveonline.models import EveCharacter
from esi.models import Token
from django.contrib import messages
import logging


logger = logging.getLogger(__name__)


def get_asset_names(character, item_ids):
    """
    Получение имен ассетов (включая структуры) через ESI endpoint
    
    Args:
        character: Объект EveCharacter
        item_ids: Список item_id для получения имен
    
    Returns:
        Словарь {item_id: {'item_id': x, 'name': y, 'type_id': z}}
    """
    from django.apps import apps
    
    if not item_ids:
        return {}
    
    try:
        eveonline_config = apps.get_app_config('eveonline')
        esi = eveonline_config.esi
        
        if not esi:
            logger.warning("ESI client не инициализирован")
            return {}
        
        # Получаем токен для запроса
        token = Token.objects.get(character_id=character.character_id)
        
        # Batch-запрос имен (ESI принимает до 1000 item_id за раз)
        # Разбиваем на части по 1000, если нужно
        all_names = {}
        for i in range(0, len(item_ids), 1000):
            batch_ids = item_ids[i:i + 1000]
            
            names_response = esi.client.Character.GetCharactersCharacterIdAssetsNames(
                character_id=character.character_id,
                item_ids=batch_ids,
                token=token
            )
            
            names_data = names_response.results()
            if hasattr(names_data, 'data'):
                names_data = names_data.data
            
            # Преобразуем в словарь {item_id: {'item_id': x, 'name': y, 'type_id': z}}
            if isinstance(names_data, list):
                batch_names = {item['item_id']: item for item in names_data}
                all_names.update(batch_names)
        
        return all_names
    except Exception as e:
        logger.error(f"Ошибка при получении имен ассетов для {character.name}: {e}")
        return {}


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
        logger.info(f"Container content: item_id={content.item_id}, type_id={content.type_id.type_id}, location.location_id={loc_id}, is_singleton={content.is_singleton}")
    
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
                    logger.info(f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=critical")
                elif qty <= warning_threshold:
                    asset.alert_level = 'warning'
                    logger.info(f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=warning")
                elif qty == thresh:
                    asset.alert_level = 'warning'
                    logger.info(f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=warning (equal to threshold)")
                else:
                    asset.alert_level = None
                    logger.info(f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, alert_level=None")
            else:
                asset.alert_level = None
                logger.info(f"Container asset alert_level: item_id={asset.item_id}, type_id={type_id}, quantity={qty}, no threshold found")
    
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
                logger.info(f"  Container asset: item_id={container_asset.item_id}, type_id={container_asset.type_id.type_id}, quantity={container_asset.quantity}, alert_level={getattr(container_asset, 'alert_level', 'NOT SET')}")
        else:
            # Это ассет на открытом пространстве
            open_assets.append(asset)
            logger.info(f"Open asset: item_id={item_id}, type_id={asset.type_id.type_id}, category_name={category_name}, alert_level={getattr(asset, 'alert_level', 'NOT SET')}")
    
    return {'open_assets': open_assets, 'container_groups': container_groups}


@app_access_required(ObserverAssetsSingleConfig.name)
@login_required
def render_traders(request):
    # Проверяем, есть ли у пользователя хотя бы один токен с нужными scopes
    has_valid_token = Token.objects.filter(
        user=request.user,
        scopes__name__in=SCOPES_FOR_TRADERS
    ).exists()
    
    if request.method == 'POST':
        form = LocationSelectForm(request.POST, user=request.user)
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
                
                # Фильтруем по group_name, если указан (множественный выбор)
                group_names = form.cleaned_data.get('group_name', [])
                # Если в списке только '' или пустой список - не фильтруем по группам
                if group_names:
                    # Фильтруем только по непустым значениям
                    real_group_names = [g for g in group_names if g]
                    if real_group_names:
                        assets = assets.filter(type_id__group_name__in=real_group_names)
                
                assets = assets.order_by('character__name', 'location__location_id', 'type_id')
                
                # Загружаем пороги алертов для текущего пользователя
                user_id = request.user.id if request.user.is_authenticated else 0
                from observer_assets_single.models import AlertThreshold
                alert_thresholds = {at.type_id_id: at.min_quantity for at in AlertThreshold.objects.filter(user_id=user_id)}
                
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
                        logger.info(f"Asset type_id={asset.type_id.type_id}, quantity={asset.quantity}, no threshold found")
                
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
                    
                    location_data[location_obj.location_id] = build_location_hierarchy(loc_assets, character, alert_thresholds)
                
                logger.info(f"Строено иерархий для локаций: {len(location_data)}")
                
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
                                        logger.info(f"Удален зафиченный шип из контейнеров: item_id={item_id}, category_name={category_name}, location_flag={location_flag}")
                            
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
        
        form = LocationSelectForm(user=request.user, initial=initial_data)
        locations_selected = []
        assets = []
    
    return render(request, 'render_traders.html', {
        'form': form,
        'locations_selected': locations_selected,
        'assets': assets,
        'location_data': location_data if locations_selected else {},
        'user_characters': EveCharacter.objects.filter(assets__isnull=False).distinct().order_by('name') if request.user.is_authenticated else [],
        'has_valid_token': has_valid_token if request.user.is_authenticated else False
    })


@app_access_required(ObserverAssetsSingleConfig.name)
@login_required
@token_required(new=True, scopes=SCOPES_FOR_TRADERS)
def get_token_assets(request, token):
    assets_status = get_personage_assets.delay(token.id)
    return redirect('observer_assets_single:render_traders')


@app_access_required(ObserverAssetsSingleConfig.name)
@login_required
def alert_settings(request):
    """Страница настройки порогов алертов"""
    from observer_assets_single.models import AlertThreshold
    
    user_id = request.user.id
    
    # Получаем все доступные предметы
    all_types = EveItemType.objects.all().order_by('type_name')
    
    # Получаем уже настроенные пороги для текущего пользователя
    existing_thresholds = AlertThreshold.objects.filter(user_id=user_id)
    existing_type_ids = set(existing_thresholds.values_list('type_id_id', flat=True))
    
    # Создаем словарь для быстрого доступа к порогам
    thresholds_dict = {et.type_id_id: et for et in existing_thresholds}
    
    # Обработка формы
    if request.method == 'POST':
        # Проверяем, редактируем ли мы существующий порог
        threshold_id = request.POST.get('threshold_id')
        
        if threshold_id:
            # Редактирование существующего порога
            try:
                threshold = AlertThreshold.objects.get(id=threshold_id, user_id=user_id)
                form = AlertThresholdForm(request.POST, instance=threshold, user=request.user)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Порог алерта успешно обновлен!')
                    return redirect('observer_assets_single:alert_settings')
                else:
                    messages.error(request, 'Ошибка при обновлении порога. Проверьте правильность данных.')
            except AlertThreshold.DoesNotExist:
                messages.error(request, 'Порог алерта не найден')
                return redirect('observer_assets_single:alert_settings')
        else:
            # Создание нового порога или обновление существующего
            form = AlertThresholdForm(request.POST, user=request.user)
            if form.is_valid():
                type_id_obj = form.cleaned_data.get('type_id')
                min_quantity = form.cleaned_data.get('min_quantity')
                
                # Проверяем, существует ли уже алерт для этого предмета
                existing_threshold = AlertThreshold.objects.filter(
                    user_id=user_id,
                    type_id=type_id_obj
                ).first()
                
                if existing_threshold:
                    # Если алерт уже существует - обновляем его
                    existing_threshold.min_quantity = min_quantity
                    existing_threshold.save()
                    messages.success(request, f'Порог алерта для "{type_id_obj.type_name}" успешно обновлен на {min_quantity}!')
                else:
                    # Создаем новый алерт
                    threshold = form.save(commit=False)
                    threshold.user_id = user_id
                    logger.info(f"Saving threshold: user_id={user_id}, type_id={threshold.type_id}, min_quantity={threshold.min_quantity}")
                    threshold.save()
                    messages.success(request, 'Порог алерта успешно добавлен!')
                return redirect('observer_assets_single:alert_settings')
            else:
                logger.error(f"Form errors: {form.errors}")
                messages.error(request, 'Ошибка при добавлении порога алерта. Проверьте правильность данных.')
    else:
        form = AlertThresholdForm()
    
    # Заполняем список предметов в форме
    form.fields['type_id'].choices = [(item.type_id, item.type_name) for item in EveItemType.objects.all().order_by('type_name')]
    
    # Добавляем поля для редактирования/удаления существующих порогов
    thresholds_list = []
    for at in existing_thresholds:
        thresholds_list.append({
            'id': at.id,
            'type_id': at.type_id_id,
            'type_name': at.type_id.type_name if at.type_id else 'Неизвестно',
            'group_name': at.type_id.group_name if at.type_id else '',
            'category_name': at.type_id.category_name if at.type_id else '',
            'min_quantity': at.min_quantity,
            'created_at': at.created_at,
        })
    
    return render(request, 'alert_settings.html', {
        'form': form,
        'all_types': all_types,
        'thresholds_list': thresholds_list,
        'existing_type_ids': existing_type_ids,
    })


def delete_threshold(request):
    """Удаление порога алерта"""
    if request.method == 'POST' and request.user.is_authenticated:
        user_id = request.user.id
        threshold_id = request.POST.get('threshold_id')
        
        try:
            AlertThreshold.objects.filter(id=threshold_id, user_id=user_id).delete()
            messages.success(request, 'Порог алерта успешно удален!')
            return redirect('observer_assets_single:alert_settings')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении порога алерта: {str(e)}')
            return redirect('observer_assets_single:alert_settings')
    
    messages.error(request, 'Неверный запрос')
    return redirect('observer_assets_single:alert_settings')


def edit_threshold(request):
    """Редактирование порога алерта"""
    if request.method == 'POST' and request.user.is_authenticated:
        user_id = request.user.id
        threshold_id = request.POST.get('threshold_id')
        min_quantity = request.POST.get('min_quantity')
        
        try:
            threshold = AlertThreshold.objects.get(id=threshold_id, user_id=user_id)
            threshold.min_quantity = min_quantity
            threshold.save()
            messages.success(request, 'Порог алерта успешно обновлен!')
        except AlertThreshold.DoesNotExist:
            messages.error(request, 'Порог алерта не найден')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении порога: {str(e)}')
        
        return redirect('observer_assets_single:alert_settings')
    
    messages.error(request, 'Неверный запрос')
    return redirect('observer_assets_single:alert_settings')






def parser_assets(assets, character):
    """
    Парсер активов для сохранения в модель Asset
    Обновляет существующие активы, удаляет устаревшие и добавляет новые
    
    Args:
        assets: Список данных активов из API
        character: Объект EveCharacter, которому принадлежат активы
    """
    from observer_assets_single.models import Asset, EveItemType, EveLocation
    
    # Получаем текущие item_id активов из API
    current_item_ids = set()

    type_ids = set()
    # Собираем все уникальные ID станций
    station_ids = set()
    # Собираем ID структур для запроса имен
    structure_item_ids = set()
    # Собираем все item_id singleton предметов (корабли, контейнеры) для запроса имен
    singleton_item_ids = set()
    for item in assets:
        if item['location_type'] == 'station':
            station_ids.add(item['location_id'])
        type_ids.add(item['type_id'])
        # Если это структура - сохраняем ID для запроса имени
        if item['location_type'] == 'structure':
            structure_item_ids.add(item['item_id'])
        # Если это singleton предмет (корабль или контейнер) - тоже сохраняем для запроса имени
        if item['is_singleton']:
            singleton_item_ids.add(item['item_id'])
    type_data = get_types_info(list(type_ids))
    #Batch-запрос информации о станциях
    stations_data = get_stations_info(list(station_ids))
    
    # Получаем имена структур через ESI
    structures_names = get_asset_names(character, list(structure_item_ids))
    
    # Собираем имена всех singleton предметов (корабли и контейнеры)
    all_asset_names = {}
    if singleton_item_ids:
        all_asset_names = get_asset_names(character, list(singleton_item_ids))
    
    for item in assets:
        # Получаем данные станции, если location_type = station
        location_name = f"Location {item['location_id']}"
        structure_name = None
        
        # Получаем тип предмета для последующего использования
        type_info = type_data.get(item['type_id'], {})
        
        # Если это структура - получаем имя из response
        if item['location_type'] == 'structure':
            struct_data = structures_names.get(item['item_id'], {})
            structure_name = struct_data.get('name')
            location_name = structure_name or f"Structure {item['location_id']}"
        
        if item['location_type'] == 'station':
            station_data = stations_data.get(item['location_id'])
            if station_data:
                location_name = station_data.get('stationName', f"Location {item['location_id']}")
            else:
                logger.warning(f"Не удалось получить данные для станции ID {item['location_id']}")
        
        # Если это контейнер/корабль (item['is_singleton'] == True), сохраним его имя в EveLocation
        # для последующего использования в аккордеоне
        if item['is_singleton']:
            container_name = all_asset_names.get(item['item_id'], {}).get('name')
            # Если имя не найдено в all_asset_names, используем имя из type_data
            if not container_name:
                container_name = type_info.get('typeName', f"Item {item['item_id']}")
            # Обновляем или создаем запись для контейнера/корабля
            loc, created = EveLocation.objects.update_or_create(
                location_id=item['item_id'],
                defaults={
                    'location_name': container_name,
                    'location_type': 'item',
                    'structure_name': container_name,
                    'is_structure': False
                }
            )
            action = "Created" if created else "Updated"
            logger.info(f"{action} EveLocation entry for item_id={item['item_id']}: name={container_name}, type=item")
        else:
            logger.info(f"Skipping item_id {item['item_id']}, is_singleton={item['is_singleton']}")
        type_name = type_info.get('typeName', f"Type {item['type_id']}")
        group_id = type_info.get('groupID')
        group_name = type_info.get('groupName', '')
        category_id = type_info.get('categoryID')
        category_name = type_info.get('categoryName', '')
        
        item_type, _ = EveItemType.objects.update_or_create(
            type_id=item['type_id'],
            defaults={
                'type_name': type_name,
                'group_id': group_id,
                'group_name': group_name,
                'category_id': category_id,
                'category_name': category_name
            }
        )
        
        # Создаем или обновляем локацию (чтобы обновлялось имя станции/структуры)
        location, _ = EveLocation.objects.update_or_create(
            location_id=item['location_id'],
            defaults={
                'location_name': location_name,
                'location_type': item['location_type'],
                'structure_name': structure_name,
                'is_structure': item['location_type'] == 'structure'
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



