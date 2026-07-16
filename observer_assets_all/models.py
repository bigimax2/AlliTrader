from django.db import models


class PriceStatistics(models.Model):
    class Meta:
        verbose_name = "Price Statistics"
        verbose_name_plural = "Price Statistics"

    def __str__(self):
        return "Price Statistics"
