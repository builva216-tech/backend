from datetime import timedelta
from unittest.mock import Mock, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.accounts.models import User
from .models import Notification, PushDevice, PushDelivery, AppRelease
from .services import notify, register_device, token_cipher, token_hash
from .delivery import deliver_one, send_fcm, InvalidDevice


class NotificationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first = User.objects.create_user(email='first@example.com', phone='+21611111111',
            full_name='First', password='A-safe-test-password12!', role='customer')
        cls.second = User.objects.create_user(email='second@example.com', phone='+21622222222',
            full_name='Second', password='A-safe-test-password12!', role='customer')

    def setUp(self):
        self.client.force_authenticate(self.first)

    def make(self, user=None, key='first'):
        return notify(user=user or self.first, event_key=key, kind='booking', title='Booking updated', body='Open bookings.')

    def device(self, user=None):
        return register_device(user=user or self.first, token='safe-device-token:1234567890', app='main', platform='android')

    def test_inbox_read_and_pagination_cannot_cross_accounts(self):
        mine, other = self.make(), self.make(self.second)
        data = self.client.get('/api/v1/notifications/').data
        self.assertEqual([i['id'] for i in data['items']], [str(mine.pk)])
        self.assertEqual(data['unread'], 1)
        self.assertEqual(self.client.post(f'/api/v1/notifications/{other.pk}/read/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/notifications/?before={other.pk}').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/notifications/?before=invalid').status_code, 400)
        self.assertEqual(self.client.post(f'/api/v1/notifications/{mine.pk}/read/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/notifications/').data['unread'], 0)

    def test_keyset_pagination_can_return_older_requests(self):
        for i in range(52): self.make(key=str(i))
        first = self.client.get('/api/v1/notifications/').data
        second = self.client.get('/api/v1/notifications/', {'before': first['next']}).data
        self.assertEqual(len(first['items']), 50)
        self.assertEqual(len(second['items']), 2)
        self.assertEqual(len({i['id'] for i in first['items'] + second['items']}), 52)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/v1/notifications/').status_code, [401, 403])

    def test_admin_devices_require_staff_and_do_not_expose_token(self):
        token = 'safe-device-token:1234567890'
        bad = self.client.post('/api/v1/devices/', {'token': token, 'app': 'admin', 'platform': 'android'}, format='json')
        self.assertEqual(bad.status_code, 400)
        good = self.client.post('/api/v1/devices/', {'token': token, 'app': 'main', 'platform': 'android'}, format='json')
        self.assertEqual(good.status_code, 201)
        self.assertNotIn(token, str(good.data))
        device = PushDevice.objects.get()
        self.assertNotEqual(device.token_encrypted, token)
        self.assertEqual(token_cipher().decrypt(device.token_encrypted.encode()).decode(), token)
        self.client.force_authenticate(self.second)
        self.client.delete('/api/v1/devices/', {'token': token}, format='json')
        device.refresh_from_db()
        self.assertTrue(device.active)

    def test_transaction_rollback_has_no_inbox_or_push(self):
        self.device()
        try:
            with transaction.atomic():
                self.make()
                raise RuntimeError('rollback')
        except RuntimeError: pass
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(PushDelivery.objects.count(), 0)

    def test_duplicate_events_are_idempotent(self):
        self.device(); self.make(); self.make()
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(PushDelivery.objects.count(), 1)

    @override_settings(FCM_ENABLED=False)
    def test_push_off_keeps_inbox_and_never_calls_provider(self):
        self.device(); self.make(); sender = Mock()
        self.assertFalse(deliver_one(sender)); sender.assert_not_called()
        self.assertEqual(Notification.objects.count(), 1)

    @override_settings(FCM_ENABLED=True)
    def test_worker_delivers_once_and_does_not_repeat_sent_job(self):
        self.device(); self.make(); sender = Mock()
        self.assertTrue(deliver_one(sender)); self.assertFalse(deliver_one(sender))
        sender.assert_called_once(); self.assertEqual(PushDelivery.objects.get().state, 'sent')

    @override_settings(FCM_ENABLED=True)
    def test_user_switch_revocation_and_password_change_skip_old_deliveries(self):
        device = self.device(); self.make()
        self.device(self.second)
        sender = Mock(); deliver_one(sender); sender.assert_not_called()
        self.assertEqual(PushDelivery.objects.get().state, 'skipped')
        self.device(); self.make(key='second-event')
        self.first.set_password('New-password-123!'); self.first.save(update_fields=['password'])
        deliver_one(sender); sender.assert_not_called()

    @override_settings(FCM_ENABLED=True)
    def test_bad_tokens_deactivate_and_transient_errors_retry_without_secret_logs(self):
        device = self.device(); self.make(); deliver_one(Mock(side_effect=InvalidDevice()))
        device.refresh_from_db(); self.assertFalse(device.active)
        self.device(); self.make(key='retry')
        deliver_one(Mock(side_effect=RuntimeError('private-token-secret')))
        job = PushDelivery.objects.get(notification__event_key='retry')
        self.assertEqual(job.state, 'queued'); self.assertEqual(job.last_error, 'delivery_unavailable')
        self.assertGreater(job.next_attempt_at, timezone.now())
        job.attempts = 4; job.next_attempt_at = timezone.now()-timedelta(seconds=1); job.save()
        deliver_one(Mock(side_effect=RuntimeError('private')))
        job.refresh_from_db(); self.assertEqual(job.state, 'failed')

    def test_real_firebase_sdk_message_is_constructed_without_network_or_token_leak(self):
        from firebase_admin import messaging
        device = self.device(); item = self.make()
        with patch('firebase_admin.get_app', return_value=object()), patch('firebase_admin.messaging.send', return_value='accepted') as send:
            send_fcm(item, device)
            message = send.call_args.args[0]
            self.assertEqual(message.token, 'safe-device-token:1234567890')
            self.assertEqual(message.data['notificationId'], str(item.pk))
            self.assertNotIn(self.first.email, message.notification.body)
        with patch('firebase_admin.get_app', return_value=object()), patch('firebase_admin.messaging.send', side_effect=messaging.UnregisteredError('expired token')):
            with self.assertRaises(InvalidDevice): send_fcm(item, device)

    def test_release_public_metadata_and_notification_are_scoped_and_idempotent(self):
        self.assertIsNone(self.client.get('/api/v1/app-release/?app=main&platform=android').data['release'])
        args = dict(app='main', platform='android', version_code=3, version_name='1.0.2',
            url='https://downloads.example.com/carrent.apk', notify=True)
        call_command('publish_app_release', **args, verbosity=0)
        call_command('publish_app_release', **args, verbosity=0)
        self.assertEqual(Notification.objects.filter(kind='app_update').count(), 2)
        self.assertEqual(self.client.get('/api/v1/app-release/').data['release']['versionCode'], 3)
        self.assertIsNone(self.client.get('/api/v1/app-release/?app=admin').data['release'])
        with self.assertRaises(CommandError):
            call_command('publish_app_release', app='main', platform='android', version_code=4,
                version_name='1.0.3', url='http://unsafe.example.com/app.apk', verbosity=0)
        self.assertFalse(AppRelease.objects.filter(version_code=4, published=True).exists())
