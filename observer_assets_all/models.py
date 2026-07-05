from django.db import models

from eveonline.models import EveCharacter


class TypeSearchResult(models.Model):
    """Модель для хранения результатов поиска типов предметов"""
    type_id = models.PositiveBigIntegerField(primary_key=True, null=False, blank=False)
    type_name = models.CharField(max_length=255, null=True, blank=True)
    group_id = models.PositiveBigIntegerField(null=True, blank=True)
    group_name = models.CharField(max_length=255, null=True, blank=True)
    category_id = models.PositiveBigIntegerField(null=True, blank=True)
    category_name = models.CharField(max_length=255, null=True, blank=True)
    search_timestamp = models.DateTimeField(auto_now_add=True)
    character = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='Список_наблюдения',
        help_text="Персонаж, которому принадлежит список"
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
