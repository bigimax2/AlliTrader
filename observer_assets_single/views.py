from django.shortcuts import render, redirect
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
from authenticated.models import OwnershipRecord
from esi.models import Token
from django.contrib import messages
import logging


logger = logging.getLogger(__name__)


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
        
        if form.is_valid():
            form.save()
            locations_selected = form.cleaned_data.get('locations', [])
            
            if locations_selected:
                # Получаем ID выбранных локаций
                location_ids = [loc.location_id for loc in locations_selected]
                location_flag = form.cleaned_data.get('location_flag', '')
                
                # Получаем ассеты для выбранных локаций
                from observer_assets_single.models import Asset
                # Получаем выбранных персонажей или всех персонажей текущего пользователя через OwnershipRecord
                selected_characters = form.cleaned_data.get('character', [])
                if selected_characters:
                    character_ids = selected_characters
                else:
                    # Получаем character_id через OwnershipRecord пользователя
                    character_ids = OwnershipRecord.objects.filter(user=request.user).values_list('character_id', flat=True).distinct()
                
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
        else:
            logger.error(f"Форма не валидна: {form.errors}")
    else:
        form = LocationSelectForm(user=request.user)
        locations_selected = []
        assets = []
    
    return render(request, 'render_traders.html', {
        'form': form,
        'locations_selected': locations_selected,
        'assets': assets,
        'user_characters': EveCharacter.objects.filter(ownership_records__user=request.user).order_by('name') if request.user.is_authenticated else [],
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
        form = AlertThresholdForm(request.POST)
        if form.is_valid():
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
        type_info = type_data.get(item['type_id'], {})
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



