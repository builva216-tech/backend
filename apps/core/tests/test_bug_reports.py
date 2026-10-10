from smtplib import SMTPException
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.core.api.bug_reports import BugReportView
from apps.core.bug_mail import deliver_next_report
from apps.core.models import BugReport


@override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BugReportTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='reporter@example.com', password='StrongPassword123!',
                                            full_name='Reporter', phone='+21690000999', role='customer')
        cls.admin = User.objects.create_superuser(email='support-admin@example.com', password='StrongPassword123!',
                                            full_name='Admin', phone='+21690000998')

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.user)
        self.payload = {'title': 'Booking button fails', 'description': 'The button does not respond.',
                        'steps': 'Open a car and tap Book.', 'appVersion': '1.0.3+4', 'platform': 'android'}

    def submit(self, payload=None):
        return self.client.post('/api/v1/support/bug-reports/', self.payload if payload is None else payload, format='json')

    def test_route_is_connected(self):
        self.assertIs(resolve('/api/v1/support/bug-reports/').func.view_class, BugReportView)

    def test_report_is_saved_before_mail_and_goes_only_to_support(self):
        response = self.submit(dict(self.payload, to='attacker@example.com', email='fake@example.com'))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['emailStatus'], 'queued')
        self.assertEqual(BugReport.objects.get().reporter_email, self.user.email)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(deliver_next_report())
        self.assertEqual(mail.outbox[-1].to, ['builva.216@gmail.com'])
        self.assertEqual(mail.outbox[-1].reply_to, [self.user.email])
        self.assertIn(self.payload['description'], mail.outbox[-1].body)
        self.assertEqual(BugReport.objects.get().email_status, 'sent')
        self.assertFalse(deliver_next_report())

    def test_anonymous_user_cannot_send(self):
        self.client.force_authenticate(None)
        self.assertIn(self.submit().status_code, (401, 403))
        self.assertFalse(BugReport.objects.exists())

    def test_invalid_and_header_injection_reports_are_rejected(self):
        for payload in ({'title': 'x', 'description': 'too short'},
                        dict(self.payload, title='Subject\nBcc: injected@example.com'),
                        dict(self.payload, description='x' * 5001)):
            self.assertEqual(self.submit(payload).status_code, 400)
        self.assertFalse(BugReport.objects.exists())

    @patch('apps.core.bug_mail.EmailMessage.send', side_effect=SMTPException('private smtp detail'))
    def test_failed_mail_preserves_report_for_retry(self, send):
        self.assertEqual(self.submit().status_code, 201)
        deliver_next_report()
        report = BugReport.objects.get()
        self.assertEqual(report.email_status, 'queued')
        self.assertEqual(report.email_attempts, 1)
        self.assertGreater(report.next_delivery_at, timezone.now())
        self.assertEqual(report.description, self.payload['description'])

    @patch('apps.core.bug_mail.EmailMessage.send', return_value=0)
    def test_zero_deliveries_does_not_claim_sent(self, send):
        self.submit()
        deliver_next_report()
        self.assertEqual(BugReport.objects.get().email_status, 'queued')

    @override_settings(DEBUG=False)
    def test_production_test_backend_does_not_claim_delivery(self):
        self.assertEqual(self.submit().status_code, 201)
        deliver_next_report()
        self.assertEqual(BugReport.objects.get().email_status, 'queued')

    def test_per_user_limit(self):
        for _ in range(5):
            self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.submit().status_code, 429)
        self.assertEqual(BugReport.objects.count(), 5)

    def test_admin_inbox_resolution_and_retry_are_protected(self):
        self.submit()
        report = BugReport.objects.get()
        self.assertEqual(self.client.get('/api/v1/admin/bug-reports/').status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/v1/admin/bug-reports/').data['count'], 1)
        BugReport.objects.filter(pk=report.pk).update(email_status='failed', email_attempts=10)
        response = self.client.patch(f'/api/v1/admin/bug-reports/{report.pk}/', {'status': 'resolved', 'retryEmail': True}, format='json')
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual((report.status, report.email_status, report.email_attempts), ('resolved', 'queued', 0))

    @patch('apps.core.bug_mail.EmailMessage.send', return_value=0)
    def test_retry_limit_and_manual_reset(self, send):
        self.submit()
        BugReport.objects.update(email_attempts=9)
        deliver_next_report()
        self.assertEqual(BugReport.objects.get().email_status, 'failed')
