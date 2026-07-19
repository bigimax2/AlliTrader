from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from observer_assets_single.models import Asset
from traders.models import TypeSearchResult


@receiver(post_save, sender=Asset)
def update_type_search_result_on_asset_save(sender, instance, **kwargs):
    """Обновление количества ассетов в TypeSearchResult при сохранении ассета"""
    try:
        type_result = TypeSearchResult.objects.get(type_id=instance.type_id.type_id)
        type_result.update_asset_count()
    except TypeSearchResult.DoesNotExist:
        pass


@receiver(post_delete, sender=Asset)
def update_type_search_result_on_asset_delete(sender, instance, **kwargs):
    """Обновление количества ассетов в TypeSearchResult при удалении ассета"""
    try:
        type_result = TypeSearchResult.objects.get(type_id=instance.type_id.type_id)
        type_result.update_asset_count()
    except TypeSearchResult.DoesNotExist:
        pass
