from django.contrib import admin
from django.utils.html import format_html
from .models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "activity_type", "group_display", "transaction_id", "formatted_comments", "created_date")
    list_filter = ("activity_type", "created_date", "group_id", "transaction_id")

    search_fields = ("user_id_id", "related_users_ids__email", "group_id__group_name", "transaction_id__id")

    date_hierarchy = "created_date"
    ordering = ("-created_date",)
    list_per_page = 50

    def formatted_comments(self, obj):
        """Display comments as JSON in a readable format"""
        if not obj.comments:  # If comments is None or empty
            return "-"

        message = obj.comments.get("message", obj.comments)  # Use the whole JSON if no "message" key
        return format_html(f"<pre>{message}</pre>")

    def group_display(self, obj):
        """Display group name instead of object reference"""
        return obj.group_id.group_name if obj.group_id else "-"
    group_display.short_description = "Group"

    fieldsets = (
        ("Activity Details", {"fields": ("user_id", "activity_type", "created_date")}),
        ("Related Entities", {"fields": ("related_users_ids", "group_id", "transaction_id")}),
        ("Comments (JSON Data)", {"fields": ("comments",)}),
    )

    readonly_fields = ("created_date",)
    filter_horizontal = ("related_users_ids",)
