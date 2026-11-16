from django.contrib import admin

from .models import Booking, Provider, Service, WorkingHours


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slot_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 1


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    filter_horizontal = ("services",)
    inlines = [WorkingHoursInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("code", "patient_name", "provider", "service", "start_at", "status")
    list_filter = ("status", "provider")
    search_fields = ("code", "patient_name", "patient_phone")
    readonly_fields = ("code", "created_at")