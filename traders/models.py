from django.db import models

from eveonline.models import EveCharacter


class TypeSearchResult(models.Model):
    """Модель для хранения результатов поиска типов предметов (общие для всех пользователей)"""
    type_id = models.PositiveBigIntegerField(primary_key=True, null=False, blank=False)
    type_name = models.CharField(max_length=255, null=True, blank=True)
    group_id = models.PositiveBigIntegerField(null=True, blank=True)
    group_name = models.CharField(max_length=255, null=True, blank=True)
    category_id = models.PositiveBigIntegerField(null=True, blank=True)
    category_name = models.CharField(max_length=255, null=True, blank=True)
    search_timestamp = models.DateTimeField(auto_now_add=True)
    character = models.ManyToManyField(
        EveCharacter,
        blank=True,
        related_name='type_search_results',
        help_text="Персонажи, добавившие этот тип в список наблюдения"
    )
    
    # Связь с ассетами для отслеживания количества предметов у персонажей
    asset_count = models.PositiveIntegerField(
        default=0,
        help_text="Общее количество этого предмета у всех персонажей, добавивших в список"
    )
    
    class Meta:
        verbose_name = "Результат поиска типа предмета"
        verbose_name_plural = "Результаты поиска типов предметов"
        indexes = [
            models.Index(fields=['type_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['category_name']),
        ]
    
    def __str__(self):
        return self.type_name or f"Type ID: {self.type_id}"
    
    def update_asset_count(self):
        """Обновление количества ассетов для этого типа предмета"""
        from observer_assets_single.models import Asset
        count = Asset.objects.filter(type_id__type_id=self.type_id).aggregate(models.Sum('quantity'))['quantity__sum']
        self.asset_count = count or 0
        self.save()


class PricesAssetsMarket(models.Model):
    type = models.OneToOneField(TypeSearchResult, on_delete=models.CASCADE, null=True, blank=True)
    minsellamarr = models.FloatField(null=True, blank=True)
    minsellhek = models.FloatField(null=True, blank=True)
    minselldodixie = models.FloatField(null=True, blank=True)
    minsellrens = models.FloatField(null=True, blank=True)
    maxbuyjita = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.type.type_name or f"Price Market: {self.type.type_name}"

    class Meta:
        verbose_name = "Price Market"
        verbose_name_plural = "Price Market"


class CoefficientsMarket(models.Model):
    coefficient = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Coefficient Market"
        verbose_name_plural = "Coefficient Market"

    def __str__(self):
        return str(self.coefficient) if self.coefficient else '0.0'
