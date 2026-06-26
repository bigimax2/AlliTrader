from django.contrib import admin

from eveonline.models import EveCharacter, EveCorporation, EveAlliance, RoleCharacters


@admin.register(EveCharacter)
class EveCharacterAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(EveCorporation)
class EveCorporationAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(EveAlliance)
class EveAllianceAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(RoleCharacters)
class RoleCharactersAdmin(admin.ModelAdmin):
    list_display = ('personage', 'ceo', 'director')