from django.contrib import admin
from otp.models import OTP
from django.utils.translation import gettext_lazy as _


class OTPAdmin(admin.ModelAdmin):
    """Define the admin pages for OTP."""
    ordering = ['-created_at']
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used', 'reason')
    search_fields = ('user__username', 'code', 'reason')
    list_filter = ('reason', 'created_at', 'expires_at')
    fieldsets = (
        (None, {'fields': ('user', 'code', 'is_used', 'reason')}),
        (_('OTP Dates'), {'fields': ('created_at', 'expires_at')}),
    )
    readonly_fields = ['created_at', 'expires_at']


admin.site.register(OTP, OTPAdmin)
