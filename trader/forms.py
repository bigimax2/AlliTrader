from django import forms
from .models import EveLocation, EveItemType


LOCATION_FLAGS = [
    ('', 'Все локации'),
    ('AssetSafety', 'Asset Safety'),
    ('AutoFit', 'Auto-fit'),
    ('BoosterBay', 'Booster Bay'),
    ('CapsuleerDeliveries', 'Capsuleer Deliveries'),
    ('Cargo', 'Cargo'),
    ('CorporationGoalDeliveries', 'Corp Goal Deliveries'),
    ('CorpseBay', 'Corpse Bay'),
    ('Deliveries', 'Deliveries'),
    ('DroneBay', 'Drone Bay'),
    ('ExpeditionHold', 'Expedition Hold'),
    ('FighterBay', 'Fighter Bay'),
    ('FighterTube0', 'Fighter Tube 0'),
    ('FighterTube1', 'Fighter Tube 1'),
    ('FighterTube2', 'Fighter Tube 2'),
    ('FighterTube3', 'Fighter Tube 3'),
    ('FighterTube4', 'Fighter Tube 4'),
    ('FleetHangar', 'Fleet Hangar'),
    ('FrigateEscapeBay', 'Frigate Escape Bay'),
    ('Hangar', 'Hangar'),
    ('HangarAll', 'Hangar All'),
    ('HiSlot0', 'Hi Slot 0'),
    ('HiSlot1', 'Hi Slot 1'),
    ('HiSlot2', 'Hi Slot 2'),
    ('HiSlot3', 'Hi Slot 3'),
    ('HiSlot4', 'Hi Slot 4'),
    ('HiSlot5', 'Hi Slot 5'),
    ('HiSlot6', 'Hi Slot 6'),
    ('HiSlot7', 'Hi Slot 7'),
    ('HiddenModifiers', 'Hidden Modifiers'),
    ('Implant', 'Implant'),
    ('InfrastructureHangar', 'Infrastructure Hangar'),
    ('LoSlot0', 'Lo Slot 0'),
    ('LoSlot1', 'Lo Slot 1'),
    ('LoSlot2', 'Lo Slot 2'),
    ('LoSlot3', 'Lo Slot 3'),
    ('LoSlot4', 'Lo Slot 4'),
    ('LoSlot5', 'Lo Slot 5'),
    ('LoSlot6', 'Lo Slot 6'),
    ('LoSlot7', 'Lo Slot 7'),
    ('Locked', 'Locked'),
    ('MedSlot0', 'Med Slot 0'),
    ('MedSlot1', 'Med Slot 1'),
    ('MedSlot2', 'Med Slot 2'),
    ('MedSlot3', 'Med Slot 3'),
    ('MedSlot4', 'Med Slot 4'),
    ('MedSlot5', 'Med Slot 5'),
    ('MedSlot6', 'Med Slot 6'),
    ('MedSlot7', 'Med Slot 7'),
    ('MobileDepotHold', 'Mobile Depot Hold'),
    ('MoonMaterialBay', 'Moon Material Bay'),
    ('QuafeBay', 'Quafe Bay'),
    ('RigSlot0', 'Rig Slot 0'),
    ('RigSlot1', 'Rig Slot 1'),
    ('RigSlot2', 'Rig Slot 2'),
    ('RigSlot3', 'Rig Slot 3'),
    ('RigSlot4', 'Rig Slot 4'),
    ('RigSlot5', 'Rig Slot 5'),
    ('RigSlot6', 'Rig Slot 6'),
    ('RigSlot7', 'Rig Slot 7'),
    ('ShipHangar', 'Ship Hangar'),
    ('Skill', 'Skill'),
    ('SpecializedAmmoHold', 'Specialized Ammo Hold'),
    ('SpecializedAsteroidHold', 'Specialized Asteroid Hold'),
    ('SpecializedCommandCenterHold', 'Specialized Command Center Hold'),
    ('SpecializedFuelBay', 'Specialized Fuel Bay'),
    ('SpecializedGasHold', 'Specialized Gas Hold'),
    ('SpecializedIceHold', 'Specialized Ice Hold'),
    ('SpecializedIndustrialShipHold', 'Specialized Industrial Ship Hold'),
    ('SpecializedLargeShipHold', 'Specialized Large Ship Hold'),
    ('SpecializedMaterialBay', 'Specialized Material Bay'),
    ('SpecializedMediumShipHold', 'Specialized Medium Ship Hold'),
    ('SpecializedMineralHold', 'Specialized Mineral Hold'),
    ('SpecializedOreHold', 'Specialized Ore Hold'),
    ('SpecializedPlanetaryCommoditiesHold', 'Specialized Planetary Commodities Hold'),
    ('SpecializedSalvageHold', 'Specialized Salvage Hold'),
    ('SpecializedShipHold', 'Specialized Ship Hold'),
    ('SpecializedSmallShipHold', 'Specialized Small Ship Hold'),
    ('StructureDeedBay', 'Structure Deed Bay'),
    ('SubSystemBay', 'Sub-System Bay'),
    ('SubSystemSlot0', 'Sub-System Slot 0'),
    ('SubSystemSlot1', 'Sub-System Slot 1'),
    ('SubSystemSlot2', 'Sub-System Slot 2'),
    ('SubSystemSlot3', 'Sub-System Slot 3'),
    ('SubSystemSlot4', 'Sub-System Slot 4'),
    ('SubSystemSlot5', 'Sub-System Slot 5'),
    ('SubSystemSlot6', 'Sub-System Slot 6'),
    ('SubSystemSlot7', 'Sub-System Slot 7'),
    ('Unlocked', 'Unlocked'),
    ('Wardrobe', 'Wardrobe'),
]

# Получаем уникальные категории и группы для фильтрации
def get_category_choices():
    categories = EveItemType.objects.exclude(category_name='').values_list('category_name', flat=True).distinct().order_by('category_name')
    return [('', 'Все категории')] + [(cat, cat) for cat in categories]

def get_group_choices():
    groups = EveItemType.objects.exclude(group_name='').values_list('group_name', flat=True).distinct().order_by('group_name')
    return [('', 'Все группы')] + [(grp, grp) for grp in groups]


class LocationSelectForm(forms.Form):
    """Форма для множественного выбора локаций из EveLocation"""
    locations = forms.ModelMultipleChoiceField(
        queryset=EveLocation.objects.filter(location_type='station').order_by('location_name'),
        widget=forms.SelectMultiple(attrs={'size': '15'}),
        required=False,
        label='Локации',
        help_text='Выберите одну или несколько станций (удерживайте Ctrl для множественного выбора)'
    )
    
    location_flag = forms.MultipleChoiceField(
        choices=LOCATION_FLAGS,
        required=False,
        label='Тип локации',
        widget=forms.SelectMultiple(attrs={'size': '15'}),
        help_text='Выберите один или несколько типов локаций (удерживайте Ctrl для множественного выбора)'
    )
    
    is_singleton = forms.ChoiceField(
        choices=[
            ('', 'Все активы'),
            ('1', 'Распакованные модули'),
            ('0', 'Не распакованные модули'),
        ],
        required=False,
        label='Тип актива',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Фильтр по типу актива (распакован или нет)'
    )
    
    category_name = forms.MultipleChoiceField(
        choices=get_category_choices,
        required=False,
        label='Категория предмета',
        widget=forms.SelectMultiple(attrs={'size': '8'}),
        help_text='Выберите одну или несколько категорий (удерживайте Ctrl для множественного выбора)'
    )
    
    group_name = forms.MultipleChoiceField(
        choices=get_group_choices,
        required=False,
        label='Группа предмета',
        widget=forms.SelectMultiple(attrs={'size': '8'}),
        help_text='Выберите одну или несколько групп (удерживайте Ctrl для множественного выбора)'
    )
    
    def clean_locations(self):
        """Валидация выбраных локаций"""
        locations = self.cleaned_data.get('locations', [])
        return locations
    
    def save(self):
        """Сохранение выбранных локаций (заглушка для сохранения в сессию или БД)"""
        if self.is_valid():
            # Здесь можно добавить логику сохранения выбранных локаций
            # Например, сохранить их в сессию пользователя
            return self.cleaned_data['locations']
        return None
