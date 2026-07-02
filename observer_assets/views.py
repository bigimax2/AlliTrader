from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from esi.models import Token

from authenticated.decorators import app_access_required
from eveonline.models import EveCharacter
from observer_assets.apps import ObserverAssetsConfig
from observer_assets.assets_forms import AssetsOverviewForm
from observer_assets.scopes_for_traders import SCOPES_FOR_TRADERS
from trader.models import EveLocation, EveItemType


@app_access_required(ObserverAssetsConfig.name)
@login_required
def assets_overview(request):
    """Представление для отображения всех ассетов всех персонажей с токенами доступа"""
    from trader.models import Asset

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
        else:
            assets = Asset.objects.none()
    else:
        form = AssetsOverviewForm(user=request.user, all_locations=all_locations, all_categories=all_categories,
                                  all_groups=all_groups, user_characters=all_characters)
        assets = Asset.objects.none()  # Не выгружаем ассеты при первом открытии

    return render(request, 'assets_overview.html', {
        'form': form,
        'assets': assets,
        'all_characters': all_characters,
        'user_characters': characters_with_assets,
        'all_locations': all_locations,
        'all_categories': all_categories,
        'all_groups': all_groups,
        'has_valid_token': has_valid_token if request.user.is_authenticated else False,
        'total_assets': assets.count(),
        'total_characters': characters_with_assets.count(),
        'is_filtered': request.method == 'POST',  # Флаг применения фильтров
    })