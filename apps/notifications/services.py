import base64
import hashlib
import hmac
from datetime import timedelta
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Notification, PushDevice, PushDelivery


def token_hash(token):
    return hmac.new(settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def password_fingerprint(user):
    return hmac.new(settings.SECRET_KEY.encode(), ('push-password-v1:' + user.password).encode(), hashlib.sha256).hexdigest()


def token_cipher():
    # Domain-separated encryption key; stable SECRET_KEY is required across restarts.
    key = hmac.new(settings.SECRET_KEY.encode(), b'carrent-push-token-v1', hashlib.sha256).digest()
    return Fernet(base64.urlsafe_b64encode(key))


@transaction.atomic
def register_device(*, user, token, app, platform):
    device, _ = PushDevice.objects.update_or_create(token_hash=token_hash(token), defaults={
        'user': user, 'token_encrypted': token_cipher().encrypt(token.encode()).decode(),
        'app': app, 'platform': platform, 'session_version': user.session_version, 'password_fingerprint': password_fingerprint(user), 'active': True,
    })
    return device


@transaction.atomic
def notify(*, user, event_key, kind, title, body, booking_id=None):
    item, created = Notification.objects.get_or_create(user=user, event_key=event_key, defaults={
        'kind': kind, 'title': title, 'body': body, 'booking_id': booking_id,
    })
    if created:
        expected_app = 'admin' if user.is_staff else 'main'
        devices = PushDevice.objects.filter(user=user, active=True, app=expected_app,
            session_version=user.session_version, last_seen__gte=timezone.now()-timedelta(days=30))
        PushDelivery.objects.bulk_create([PushDelivery(notification=item, device=d, next_attempt_at=timezone.now()) for d in devices])
    return item


def booking_event(event):
    booking = event.booking
    labels = {'requested': 'Booking request received', 'approved': 'Booking approved',
        'confirmed': 'Pickup confirmed', 'rejected': 'Booking request declined',
        'cancelled': 'Booking cancelled', 'active': 'Your rental has started', 'completed': 'Rental completed'}
    for user in (booking.customer, booking.agency.user):
        notify(user=user, event_key=f'booking:{event.id}', kind='booking',
            title=labels.get(event.to_status, 'Booking updated'),
            body='Open your bookings to view the latest status.', booking_id=booking.id)
