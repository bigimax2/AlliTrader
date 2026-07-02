from django import forms


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


class AssetsOverviewForm(forms.Form):
    """Форма для фильтрации ассетов в overview"""
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        all_locations = kwargs.pop('all_locations', None)
        all_categories = kwargs.pop('all_categories', None)
        all_groups = kwargs.pop('all_groups', None)
        user_characters = kwargs.pop('user_characters', None)
        
        super().__init__(*args, **kwargs)
        
        # Поля формы
        self.fields['character'] = forms.MultipleChoiceField(
            choices=[('__all__', 'Выбрать всех')] + [(char.character_id, char.name) for char in user_characters] if user_characters else [],
            required=False,
            label='Персонаж',
            widget=forms.SelectMultiple(attrs={'size': '8', 'class': 'form-select'}),
            help_text='Выберите одного или нескольких персонажей'
        )
        
        self.fields['locations'] = forms.MultipleChoiceField(
            choices=[('__all__', 'Выбрать все')] + [(loc.location_id, loc.location_name) for loc in all_locations] if all_locations else [],
            required=False,
            label='Локации',
            widget=forms.SelectMultiple(attrs={'size': '10', 'class': 'form-select'}),
            help_text='Выберите одну или несколько станций'
        )
        
        self.fields['location_flag'] = forms.MultipleChoiceField(
            choices=LOCATION_FLAGS,
            required=False,
            label='Тип локации',
            widget=forms.SelectMultiple(attrs={'size': '8', 'class': 'form-select'}),
            help_text='Выберите один или несколько типов локаций'
        )
        
        self.fields['is_singleton'] = forms.ChoiceField(
            choices=[
                ('', 'Все активы'),
                ('1', 'Распакованные модули'),
                ('0', 'Не распакованные модули'),
            ],
            required=False,
            label='Тип актива',
            widget=forms.Select(attrs={'class': 'form-select'}),
            help_text='Фильтр по типу актива'
        )
        
        self.fields['category_name'] = forms.MultipleChoiceField(
            choices=[('', 'Все категории')] + [(cat, cat) for cat in all_categories] if all_categories else [],
            required=False,
            label='Категория предмета',
            widget=forms.SelectMultiple(attrs={'size': '8', 'class': 'form-select'}),
            help_text='Выберите одну или несколько категорий'
        )
        
        self.fields['group_name'] = forms.MultipleChoiceField(
            choices=[('', 'Все группы')] + [(grp, grp) for grp in all_groups] if all_groups else [],
            required=False,
            label='Группа предмета',
            widget=forms.SelectMultiple(attrs={'size': '8', 'class': 'form-select'}),
            help_text='Выберите одну или несколько групп'
        )
