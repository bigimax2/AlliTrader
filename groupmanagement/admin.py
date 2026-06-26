from django.contrib import admin, messages
from django.contrib.auth.models import Group as BaseGroup
from django.db import transaction

from authenticated.models import State
from groupmanagement.models import NiceGroup, GroupApplication


class NiceGroupInlineAdmin(admin.StackedInline):
    model = NiceGroup
    filter_horizontal = ('users', 'group_leaders', 'states',)
    fields = (
        'users',
        'group_leaders',
        'states',
        'description',
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "states":
            # Исключаем определённые состояния, например, по имени или id
            kwargs["queryset"] = State.objects.exclude(name__in=['Guest'])
            # Или, например, по ID: .exclude(id__in=[1, 2, 3])
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class GroupAdmin(admin.ModelAdmin):
    inlines = [NiceGroupInlineAdmin]
    filter_horizontal = ('permissions',)
    fields = ('name', 'permissions')



class Group(BaseGroup):
    class Meta:
        proxy = True


try:
    admin.site.unregister(BaseGroup)
except admin.sites.NotRegistered:
    pass  # Можно игнорировать, если группа уже не зарегистрирована

admin.site.register(Group, GroupAdmin)

@admin.register(GroupApplication)
class GroupApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'group_name', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'group', 'created_at')
    #list_editable = ('status',)  # Позволяет менять статус прямо в списке
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'group__group__name')
    readonly_fields = ('user', 'group', 'created_at')
    actions = ['approve_applications', 'reject_applications']

    def group_name(self, obj):
        return obj.group.group.name
    group_name.short_description = 'Группа'

    def save_model(self, request, obj, form, change):
        """
        Вызывается при сохранении объекта в админке (в т.ч. при нажатии "Сохранить").
        Здесь обрабатываем добавление/удаление пользователя из групп при смене статуса.
        """
        if not change:
            # Это создание новой заявки — просто сохраняем
            super().save_model(request, obj, form, change)
            return

        # Сохраняем старый статус
        old_status = GroupApplication.objects.get(pk=obj.pk).status if change else None

        # Сохраняем объект (новый статус)
        super().save_model(request, obj, form, change)

        try:
            django_group = obj.group.group  # auth.Group
            nice_group = obj.group  # NiceGroup

            if obj.status == 'approved' and old_status != 'approved':
                # Добавляем пользователя
                nice_group.users.add(obj.user)
                django_group.user_set.add(obj.user)
                self.message_user(
                    request,
                    f"✅ Пользователь {obj.user} добавлен в группу {django_group.name}.",
                    level=messages.SUCCESS
                )
                # Удаляем заявку после успешного добавления
                obj.delete()

            elif old_status == 'approved' and obj.status != 'approved':
                # Был одобрен, но статус изменили — удаляем
                nice_group.users.remove(obj.user)
                django_group.user_set.remove(obj.user)
                self.message_user(
                    request,
                    f"❌ Пользователь {obj.user} удалён из группы {django_group.name}.",
                    level=messages.WARNING
                )

        except Exception as e:
            self.message_user(
                request,
                f"❌ Ошибка при обработке прав: {e}",
                level=messages.ERROR
            )

    # Действие: одобрить заявки
    @admin.action(description='Одобрить выбранные заявки')
    def approve_applications(self, request, queryset):
        with transaction.atomic():
            success_count = 0
            for app in queryset.filter(status='approved'):
                try:
                    # Добавляем в кастомную группу NiceGroup
                    app.group.users.add(app.user)

                    # Добавляем в связанную auth.Group (для permissions)
                    django_group = app.group.group  # Это auth.Group
                    django_group.user_set.add(app.user)

                    # Обновляем статус заявки
                    app.status = 'approved'
                    app.save()

                    success_count += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f"Ошибка при одобрении заявки {app.user} в группу {app.group}: {e}",
                        level=messages.ERROR
                    )

            if success_count > 0:
                self.message_user(
                    request,
                    f"Успешно одобрено {success_count} заявок.",
                    level=messages.SUCCESS
                )

    @admin.action(description='Отклонить выбранные заявки')
    def reject_applications(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        if updated:
            self.message_user(request, f"Отклонено {updated} заявок.")