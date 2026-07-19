from django.contrib import admin
from traders.models import TypeSearchResult, PricesAssetsMarket, CoefficientsMarket


@admin.register(TypeSearchResult)
class TypeSearchResultAdmin(admin.ModelAdmin):
    list_display = ('type_id', 'type_name', 'group_name', 'category_name', 'search_timestamp')
    list_filter = ('category_name', 'group_name', 'search_timestamp')
    search_fields = ('type_name', 'group_name', 'category_name')
    filter_horizontal = ('character',)


@admin.register(PricesAssetsMarket)
class PricesAssetsMarketAdmin(admin.ModelAdmin):
    list_display = ('type', 'maxbuyjita', 'minsellhek', 'minsellamarr', 'minselldodixie', 'minsellrens')
    search_fields = ('type__type_name',)


@admin.register(CoefficientsMarket)
class CoefficientsMarketAdmin(admin.ModelAdmin):
    list_display = ('coefficient',)
    list_display_links = ('coefficient',)
