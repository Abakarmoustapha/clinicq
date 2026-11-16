from django.contrib import admin

from .models import Provider, Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slot_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    filter_horizontal = ("services",)