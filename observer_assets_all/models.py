from django.db import models


class ObserverSettings(models.Model):
    """Настройки для Observer Assets"""
    key = models.CharField(max_length=100, unique=True, verbose_name='Ключ')
    value = models.TextField(blank=True, verbose_name='Значение')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Настройка наблюдателя'
        verbose_name_plural = 'Настройки наблюдателя'
    
    def __str__(self):
        return self.key
