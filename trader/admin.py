from django.contrib import admin
from .models import EveItemType, EveLocation, Asset


@admin.register(EveItemType)
class EveItemTypeAdmin(admin.ModelAdmin):
    list_display = ('type_id', 'type_name', 'published')
    list_filter = ('published',)
    search_fields = ('type_id', 'type_name')
    ordering = ('type_id',)


@admin.register(EveLocation)
class EveLocationAdmin(admin.ModelAdmin):
    list_display = ('location_id', 'location_name', 'location_type')
    list_filter = ('location_type',)
    search_fields = ('location_id', 'location_name')
    ordering = ('location_id',)


class AssetAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'is_singleton', 'type_id', 'location', 'quantity', 'character', 'corporation')
    list_filter = ('is_singleton', 'location', 'location_flag', 'character', 'corporation')
    search_fields = ('item_id', 'type_id', 'location__location_name')
    ordering = ('-item_id',)
    list_select_related = ('character', 'corporation', 'location')


admin.site.register(Asset, AssetAdmin)
