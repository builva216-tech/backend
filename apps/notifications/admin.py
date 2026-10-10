from django.contrib import admin
from .models import AppRelease, Notification, PushDelivery


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = ['app', 'platform', 'version_name', 'version_code', 'published']
    list_filter = ['app', 'platform', 'published']
    # Publishing a metadata record does not broadcast automatically. Use publish_app_release.


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['kind', 'title', 'created_at', 'read_at']
    readonly_fields = ['user', 'event_key', 'kind', 'title', 'body', 'booking_id', 'created_at', 'read_at']
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(PushDelivery)
class PushDeliveryAdmin(admin.ModelAdmin):
    list_display = ['state', 'attempts', 'last_error', 'next_attempt_at']
    readonly_fields = ['notification', 'device', 'state', 'attempts', 'next_attempt_at', 'claimed_until', 'last_error']
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
