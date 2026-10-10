import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from urllib.parse import urlsplit


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event_key = models.CharField(max_length=180)
    kind = models.CharField(max_length=32)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=240)
    booking_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['user', 'event_key'], name='notification_user_event')]
        indexes = [models.Index(fields=['user', 'read_at', '-created_at'])]


class PushDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    token_encrypted = models.TextField()
    app = models.CharField(max_length=16, choices=[('main', 'Main'), ('admin', 'Admin')])
    platform = models.CharField(max_length=8, choices=[('android', 'Android'), ('ios', 'iOS')])
    session_version = models.PositiveIntegerField(default=0)
    password_fingerprint = models.CharField(max_length=64)
    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)


class PushDelivery(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    device = models.ForeignKey(PushDevice, on_delete=models.CASCADE)
    state = models.CharField(max_length=16, default='queued')
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    claimed_until = models.DateTimeField(null=True)
    # Error codes only: never store SDK exceptions containing a token or credentials.
    last_error = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['notification', 'device'], name='push_notification_device')]
        indexes = [models.Index(fields=['state', 'next_attempt_at'])]


class AppRelease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.CharField(max_length=16, choices=[('main', 'Main'), ('admin', 'Admin')])
    platform = models.CharField(max_length=8, choices=[('android', 'Android'), ('ios', 'iOS')])
    version_code = models.PositiveIntegerField()
    version_name = models.CharField(max_length=32)
    update_url = models.URLField(max_length=1000)
    notes = models.CharField(max_length=500, blank=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['app', 'platform', 'version_code'], name='release_app_platform_version')]

    def clean(self):
        u = urlsplit(self.update_url)
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment:
            raise ValidationError({'update_url': 'Use an HTTPS store or signed-APK download link.'})
        if self.version_code < 1:
            raise ValidationError({'version_code': 'Use a positive, increasing build number.'})
