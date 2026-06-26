from django.contrib import admin
from django.contrib.auth.models import User

from authenticated.models import State, UserProfile, OwnershipRecord, Notification


@admin.register(OwnershipRecord)
class OwnershipRecordAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ('user','character', )
    list_filter = ('user', 'character')

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_select_related = True
    fieldsets = (
        (None, {'fields': ('name', 'permissions', 'priority')}),
        ('Membership', {'fields': ('member_characters', 'member_corporations', 'member_alliance')}),
    )
    filter_horizontal = ('permissions', 'member_characters', 'member_corporations', 'member_alliance')

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль юзера'

class UserAdmin(admin.ModelAdmin):
    inlines = (UserProfileInline, )

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'notification_type', 'is_read', 'system_message', 'created_at')
    list_filter = ('notification_type', 'is_read', 'system_message', 'created_at')
    search_fields = ('message', 'user__username')
    list_per_page = 25
    
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Информация', {
            'fields': ('user', 'message', 'notification_type', 'system_message')
        }),
        ('Статус', {
            'fields': ('is_read', 'created_at')
        }),
    )