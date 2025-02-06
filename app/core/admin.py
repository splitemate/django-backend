from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from group.models import GroupParticipant
from core import models


class GroupParticipantInlineForUser(admin.TabularInline):
    model = GroupParticipant
    extra = 0
    fields = ('group', 'role')
    autocomplete_fields = ['group']


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""
    ordering = ['id']
    list_display = ['email', 'name']

    inlines = [GroupParticipantInlineForUser]

    fieldsets = (
        (None, {'fields': ('name', 'email', 'password', 'invite_token')}),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
            )
        }),
        (_('Login Info'), {'fields': ('is_email_verified', 'user_source',)}),
        (_('Friends'), {'fields': ('friends',)}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    readonly_fields = ['last_login']
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'name',
                'is_active',
                'is_staff',
                'user_source'
            )
        }),
    )
    filter_horizontal = ('friends',)


admin.site.register(models.User, UserAdmin)
