from django import forms

from traders.models import CoefficientsMarket


class TypeNamesForm(forms.Form):
    """Форма для ввода списка имен предметов и передачи в get_types_names"""

    type_names = forms.CharField(
        label='Имена предметов',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Введите имена предметов, по одному на строку\nПример:\nIsis\nMaelstrom\nVindicator'
        }),
        help_text='Введите имена предметов, по одному на строку (необязательно при выборе "Из ассетов")',
        required=False
    )
    
    source_type = forms.ChoiceField(
        label='Источник предметов',
        choices=[
            ('manual', 'Вручную (из формы)'),
            ('assets', 'Из ассетов персонажа'),
        ],
        widget=forms.RadioSelect,
        initial='manual',
        required=False,
        help_text='Выберите, откуда брать предметы для поиска'
    )


class CoefficientForm(forms.Form):
    """Форма для редактирования коэффициента - доступна только суперюзеру"""
    
    coefficient = forms.FloatField(
        label='Коэффициент',
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={'step': '0.1'})
    )
