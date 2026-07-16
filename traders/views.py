from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from EVE_Online_SQLite_API import get_types_names
from authenticated.decorators import app_access_required
from eveonline.models import EveCharacter
from traders.apps import TradersConfig
from traders.forms import TypeNamesForm
from traders.models import TypeSearchResult


@app_access_required(TradersConfig.name)
@login_required
@require_http_methods(["POST"])
def delete_selected_type_search_results(request):
    """Массовое удаление записей из TypeSearchResult"""
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

        # Удаляем только записи текущего пользователя
        deleted_count, _ = TypeSearchResult.objects.filter(
            type_id__in=type_ids,
            character__character_id=personage
        ).delete()

        messages.success(request, f'Удалено {deleted_count} предмет(ов) из списка')

    except Exception as e:
        messages.error(request, f'Ошибка удаления: {e}')

    return redirect('traders:type_names_lookup')


@app_access_required(TradersConfig.name)
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