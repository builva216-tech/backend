from django.contrib import admin

from .models import BugReport


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'reporter_email', 'status', 'email_status', 'created_at')
    list_filter = ('status', 'email_status', 'platform')
    search_fields = ('title', 'description', 'reporter_email')
    readonly_fields = ('id', 'reporter', 'reporter_email', 'reporter_name', 'reporter_role',
                       'title', 'description', 'steps', 'app_version', 'platform',
                       'email_status', 'email_attempts', 'next_delivery_at', 'emailed_at', 'created_at')

    def has_add_permission(self, request):
        return False
