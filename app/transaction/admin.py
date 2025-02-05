from django.contrib import admin
from transaction.models import Transaction, TransactionParticipant, UserBalance


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
