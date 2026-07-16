from django.db import models
from eveonline.models import EveCharacter


class AssetRecord(models.Model):
    """
    Модель для хранения записей активов персонажей.
    """
    character = models.ForeignKey(EveCharacter, on_delete=models.CASCADE, related_name='asset_records', verbose_name='Персонаж')
    type_id = models.IntegerField('ID типа объекта')
    type_name = models.CharField('Название типа', max_length=255, blank=True)
    quantity = models.BigIntegerField('Количество')
    location_id = models.BigIntegerField('ID локации')
    location_name = models.CharField('Название локации', max_length=255, blank=True)
    is_blueprint = models.BooleanField('Чертеж', default=False)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Запись актива'
        verbose_name_plural = 'Записи активов'
        indexes = [
            models.Index(fields=['character', 'type_id']),
            models.Index(fields=['location_id']),
        ]

    def __str__(self):
        return f'{self.character}: {self.type_name} x{self.quantity}'
