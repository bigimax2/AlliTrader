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
    container_assets = all_location_assets.filter(is_singleton=True)
    
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
        # Получаем ассеты внутри текущих контейнеров
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
    
    # Объединяем исходные ассеты и ассеты из контейнеров
    # Добавляем флаг is_container_asset для различия
    logger.info(f"add_alerts_to_assets: open_assets count={assets.count() if hasattr(assets, 'count') else len(assets)}")
    logger.info(f"add_alerts_to_assets: container_contents count={container_contents.count() if hasattr(container_contents, 'count') else len(container_contents)}")
    logger.info(f"add_alerts_to_assets: container_ids={list(container_ids)[:10]}")
    
    all_assets = list(assets)
    for asset in container_contents:
        asset.is_container_asset = True
        all_assets.append(asset)
        logger.info(f"Container asset: item_id={asset.item_id}, type_id={asset.type_id_id}, quantity={asset.quantity}, location={asset.location.location_name}")
    
    return all_assets
