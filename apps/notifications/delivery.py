from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import PushDelivery, PushDevice
from .services import token_cipher, password_fingerprint


class InvalidDevice(Exception):
    pass


def send_fcm(item, device):
    import firebase_admin
    from firebase_admin import credentials, messaging
    try:
        app = firebase_admin.get_app('carrent-push')
    except ValueError:
        if not settings.FCM_CREDENTIALS_FILE:
            raise RuntimeError('missing_credentials')
        app = firebase_admin.initialize_app(credentials.Certificate(settings.FCM_CREDENTIALS_FILE),
            options={'httpTimeout': 15}, name='carrent-push')
    try:
        message = messaging.Message(
            token=token_cipher().decrypt(device.token_encrypted.encode()).decode(),
            notification=messaging.Notification(title=item.title, body=item.body),
            data={'notificationId': str(item.id), 'kind': item.kind,
                'bookingId': str(item.booking_id) if item.booking_id else ''},
            android=messaging.AndroidConfig(ttl=timedelta(hours=12), priority='normal'),
            apns=messaging.APNSConfig(payload=messaging.APNSPayload(aps=messaging.Aps(sound='default'))),
        )
        messaging.send(message, app=app)
    except messaging.UnregisteredError as exc:
        raise InvalidDevice() from exc


def deliver_one(sender=send_fcm):
    if not settings.FCM_ENABLED:
        return False
    now = timezone.now()
    with transaction.atomic():
        job = (PushDelivery.objects.select_for_update(skip_locked=True)
            .filter(Q(state='queued', next_attempt_at__lte=now) |
                    Q(state='sending', claimed_until__lte=now)).order_by('id').first())
        if job is None:
            return False
        job.state = 'sending'
        job.attempts += 1
        job.claimed_until = now + timedelta(minutes=2)
        job.save(update_fields=['state', 'attempts', 'claimed_until'])
    # No DB lock held over network. Lease lets a crashed worker recover.
    job = PushDelivery.objects.select_related('notification__user', 'device__user').get(pk=job.pk)
    device, item = job.device, job.notification
    allowed = (device.active and device.user_id == item.user_id and device.user.is_active
        and device.session_version == device.user.session_version
        and device.password_fingerprint == password_fingerprint(device.user)
        and device.last_seen >= now - timedelta(days=30))
    result, error = 'sent', ''
    if not allowed:
        result = 'skipped'
    else:
        try:
            sender(item, device)
        except InvalidDevice:
            result, error = 'skipped', 'device_unregistered'
            PushDevice.objects.filter(pk=device.pk, token_hash=device.token_hash).update(active=False)
        except Exception:
            # Never log raw provider exceptions: they may contain registration tokens.
            result, error = ('failed' if job.attempts >= 5 else 'queued'), 'delivery_unavailable'
    PushDelivery.objects.filter(pk=job.pk, state='sending', attempts=job.attempts).update(
        state=result, last_error=error, claimed_until=None,
        next_attempt_at=now + timedelta(seconds=min(3600, 30 * 2 ** job.attempts)))
    return True
