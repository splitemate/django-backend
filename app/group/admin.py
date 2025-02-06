from django.contrib import admin
from group.models import Group, GroupParticipant


class GroupParticipantInline(admin.TabularInline):
    model = GroupParticipant
    extra = 1
    fields = ('user', 'role')
    autocomplete_fields = ['user']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'created_by', 'group_type', 'is_active', 'created_at')
    list_filter = ('group_type', 'is_active', 'created_at')
    search_fields = ('group_name', 'created_by__username')
    inlines = [GroupParticipantInline]
    readonly_fields = ('created_at', 'updated_at')
    actions = ["restore_groups"]

    def delete_queryset(self, request, queryset):
        """Override bulk delete action to perform soft delete"""
        for obj in queryset:
            obj.delete()

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Show all groups (both active and inactive) in the admin panel."""
        return Group.all_objects.all()

    @admin.action(description="Restore selected groups")
    def restore_groups(self, request, queryset):
        """Restore selected groups from soft delete"""
        for group in queryset:
            group.is_active = True
            group.save()
