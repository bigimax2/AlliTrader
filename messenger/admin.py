from django.contrib import admin

from authenticated.models import State
from groupmanagement.admin import Group
from .models import MemberMessenger, MessengerServer, ServerAccessGroup


@admin.register(MemberMessenger)
class MemberMessengerAdmin(admin.ModelAdmin):
    list_display = ('user', 'messenger_user', 'messenger_user_id', 'last_updated')
    search_fields = ('user__username', 'messenger_user')
    list_filter = ('last_updated',)
    readonly_fields = ('last_updated',)

@admin.register(MessengerServer)
class MessengerServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'server_id', 'created_at')
    search_fields = ('name', 'owner__username')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

@admin.register(ServerAccessGroup)
class ServerAccessGroupAdmin(admin.ModelAdmin):
    list_display = ('server', 'group', 'state')
    search_fields = ('server__name', 'group__name', 'state__name')
    list_filter = ('server', 'group', 'state')
    list_select_related = True

    def get_search_results(self, request, queryset, search_term):
        # Используем стандартный поиск с возможностью расширения
        return super().get_search_results(request, queryset, search_term)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Опционально: фильтрация выпадающих списков в админке
        if db_field.name == "server":
            kwargs["queryset"] = MessengerServer.objects.all().order_by('name')
        elif db_field.name == "group":
            kwargs["queryset"] = Group.objects.all().order_by('name')
        elif db_field.name == "state":
            kwargs["queryset"] = State.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)