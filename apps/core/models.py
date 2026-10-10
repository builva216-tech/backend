import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class StoredUpload(models.Model):
    """Small private uploads backed up with the database, never publicly listed."""

    name = models.CharField(max_length=500, primary_key=True)
    content = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class BugReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reporter_email = models.EmailField()
    reporter_name = models.CharField(max_length=150)
    reporter_role = models.CharField(max_length=20)
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=5000)
    steps = models.TextField(max_length=3000, blank=True)
    app_version = models.CharField(max_length=60, blank=True)
    platform = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=10, choices=[('open', 'Open'), ('resolved', 'Resolved')], default='open')
    email_status = models.CharField(max_length=10, choices=[('queued', 'Queued'), ('sent', 'Sent'), ('failed', 'Failed')], default='queued')
    email_attempts = models.PositiveSmallIntegerField(default=0)
    next_delivery_at = models.DateTimeField(default=timezone.now, db_index=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
