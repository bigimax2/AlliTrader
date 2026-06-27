from django.db import models
from eveonline.models import EveCharacter, EveCorporation


class EveItemType(models.Model):
    """Модель для хранения типов предметов EVE Online"""
    type_id = models.PositiveIntegerField(primary_key=True, null=False, blank=False)
    type_name = models.CharField(max_length=255, null=True, blank=True)
    published = models.BooleanField(default=True, null=True, blank=True)

    class Meta:
        verbose_name = "Тип предмета"
        verbose_name_plural = "Типы предметов"

    def __str__(self):
        return self.type_name or f"Type ID: {self.type_id}"


class EveLocation(models.Model):
    """Модель для хранения локаций (станции, сектора и т.д.)"""
    location_id = models.PositiveBigIntegerField(primary_key=True, null=False, blank=False)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    location_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Локация"
        verbose_name_plural = "Локации"

    def __str__(self):
        return self.location_name or f"Location ID: {self.location_id}"


class Asset(models.Model):
    """Модель для хранения информации об активах (инвентаре) персонажей/корпораций"""
    is_singleton = models.BooleanField(null=False, blank=False)
    item_id = models.PositiveBigIntegerField(null=False, blank=False, unique=True)
    
    location_flag = models.CharField(max_length=50, null=True, blank=True)
    location_id = models.PositiveBigIntegerField(null=False, blank=False)
    location_type = models.CharField(max_length=50, null=True, blank=True)
    
    quantity = models.IntegerField(null=False, blank=False, default=1)
    
    type_id = models.PositiveBigIntegerField(null=False, blank=False)
    
    # Связи с другими моделями
    character = models.ForeignKey(
        EveCharacter, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='assets',
        help_text="Персонаж, которому принадлежит актив"
    )
    corporation = models.ForeignKey(
        EveCorporation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assets',
        help_text="Корпорация, которой принадлежит актив"
    )
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Актив"
        verbose_name_plural = "Активы"
        indexes = [
            models.Index(fields=['is_singleton']),
            models.Index(fields=['location_id']),
            models.Index(fields=['type_id']),
            models.Index(fields=['character']),
            models.Index(fields=['corporation']),
        ]

    def __str__(self):
        return f"{self.type_id} x{self.quantity} @ {self.location_id}"
