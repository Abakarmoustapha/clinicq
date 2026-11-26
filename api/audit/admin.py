from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "booking_code", "status_after", "actor_email")
    list_filter = ("action",)
    search_fields = ("booking_code", "actor_email")
    date_hierarchy = "created_at"

    # The history can be read here, but never added to, edited or deleted.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False