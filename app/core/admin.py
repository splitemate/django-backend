from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from otp.models import OTP
from group.models import Group, GroupParticipant
from transaction.models import Transaction, TransactionParticipant, UserBalance
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

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class OTPAdmin(admin.ModelAdmin):
    """Define the admin pages for OTP."""
    ordering = ['-created_at']
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used','reason')
    search_fields = ('user__username', 'code', 'reason')
    list_filter = ('reason', 'created_at', 'expires_at')
    fieldsets = (
        (None, {'fields': ('user', 'code', 'is_used', 'reason')}),
        (_('OTP Dates'), {'fields': ('created_at','expires_at')}),
    )
    readonly_fields = ['created_at', 'expires_at']
    
admin.site.register(OTP, OTPAdmin)

class TransactionParticipantInline(admin.TabularInline):
    model = TransactionParticipant
    extra = 1
    fields = ('user', 'amount_owed',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('payer', 'total_amount', 'transaction_type', 'transaction_date', 'created_by')
    list_filter = ('transaction_type', 'transaction_date')
    search_fields = ('payer__username', 'description')
    inlines = [TransactionParticipantInline]
    date_hierarchy = 'transaction_date'
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(TransactionParticipant)
class TransactionParticipantAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'user', 'amount_owed')
    search_fields = ('user__username', 'transaction__description')


class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ('initiator', 'participant', 'balance', 'total_amount_paid', 'total_amount_received', 'transaction_count', 'last_transaction_date')
    search_fields = ('initiator__username', 'participant__username')
    list_filter = ('is_active', 'last_transaction_date')
    readonly_fields = ('initiator', 'participant', 'balance', 'total_amount_paid', 'total_amount_received', 'transaction_count', 'last_transaction_date')
    
    def has_add_permission(self, request):
        return False

admin.site.register(UserBalance, UserBalanceAdmin)
