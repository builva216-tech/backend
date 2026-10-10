import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountAuditEvent, PasswordRecoveryChallenge, User
from apps.accounts.recovery import recovery_code


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordRecoveryApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            role="customer",
            email="person@example.com",
            phone="+21620123456",
            full_name="Customer Person",
            password="InitialPassword123!",
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            phone="+21620999999",
            full_name="Admin Person",
            password="InitialAdminPassword123!",
        )

    def request(self, email=None, namespace="accounts-api"):
        return self.client.post(
            reverse(namespace + ":password-recovery-request"),
            {"email": email or self.customer.email},
            format="json",
        )

    def confirm(
        self,
        challenge,
        code=None,
        password="NewUniquePassword456!",
        namespace="accounts-api",
    ):
        return self.client.post(
            reverse(namespace + ":password-recovery-confirm"),
            {
                "challengeId": str(challenge.id),
                "code": code or recovery_code(challenge, self.customer),
                "newPassword": password,
            },
            format="json",
        )

    def challenge(self):
        response = self.request()
        self.assertEqual(response.status_code, 202)
        return PasswordRecoveryChallenge.objects.get(id=response.data["challengeId"])

    def test_unknown_blocked_and_wrong_role_requests_are_generic(self):
        known = self.request()
        unknown = self.request("unknown@example.com")
        wrong = self.request(self.admin.email)
        self.customer.is_active = False
        self.customer.save()
        blocked = self.request()
        for response in [known, unknown, wrong, blocked]:
            self.assertEqual(response.status_code, 202)
            self.assertEqual(
                set(response.data),
                {"challengeId", "message", "expiresInSeconds", "resendAfterSeconds"},
            )
            self.assertEqual(response.data["message"], known.data["message"])
        self.assertEqual(
            PasswordRecoveryChallenge.objects.filter(user__isnull=False).count(), 1
        )

    def test_worker_sends_code_confirmation_and_no_replay(self):
        challenge = self.challenge()
        self.assertNotEqual(
            challenge.code_hash, recovery_code(challenge, self.customer)
        )
        call_command("send_password_recovery_emails", verbosity=0)
        code = re.search(r"\b\d{8}\b", mail.outbox[0].body).group()
        self.assertEqual(self.confirm(challenge, code).status_code, 200)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("NewUniquePassword456!"))
        self.assertEqual(self.confirm(challenge, code).status_code, 400)
        call_command("send_password_recovery_emails", verbosity=0)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("was changed", mail.outbox[1].subject)
        self.assertTrue(
            AccountAuditEvent.objects.filter(
                subject=self.customer, action="password_recovered"
            ).exists()
        )

    def test_incorrect_attempts_commit_and_lock_after_five(self):
        challenge = self.challenge()
        right = recovery_code(challenge, self.customer)
        wrong = "11111111" if right != "11111111" else "22222222"
        for _ in range(5):
            self.assertEqual(self.confirm(challenge, wrong).status_code, 400)
        challenge.refresh_from_db()
        self.assertEqual(challenge.attempts_remaining, 0)
        self.assertEqual(self.confirm(challenge, right).status_code, 400)

    def test_expired_and_weak_password_preserve_password(self):
        challenge = self.challenge()
        self.assertEqual(self.confirm(challenge, password="12345678").status_code, 400)
        challenge.refresh_from_db()
        self.assertIsNone(challenge.used_at)
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save()
        self.assertEqual(self.confirm(challenge).status_code, 400)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("InitialPassword123!"))

    def test_reset_rejects_old_access_and_refresh(self):
        refresh = RefreshToken.for_user(self.customer)
        access = str(refresh.access_token)
        challenge = self.challenge()
        self.assertEqual(self.confirm(challenge).status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access)
        self.assertEqual(self.client.get(reverse("accounts-api:me")).status_code, 401)
        self.client.credentials()
        response = self.client.post(
            reverse("accounts-api:token-refresh"),
            {"refreshToken": str(refresh)},
            format="json",
        )
        self.assertIn(response.status_code, [400, 401])

    def test_admin_reset_and_refresh_role_boundary(self):
        response = self.request(self.admin.email, "admin-portal-api")
        challenge = PasswordRecoveryChallenge.objects.get(
            id=response.data["challengeId"]
        )
        code = recovery_code(challenge, self.admin)
        self.assertEqual(
            self.confirm(challenge, code, namespace="accounts-api").status_code, 400
        )
        self.assertEqual(
            self.confirm(challenge, code, namespace="admin-portal-api").status_code, 200
        )
        self.admin.refresh_from_db()
        refresh = RefreshToken.for_user(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("admin-portal-api:token-refresh"),
                {"refreshToken": str(refresh)},
                format="json",
            ).status_code,
            200,
        )
        customer_token = RefreshToken.for_user(self.customer)
        self.assertIn(
            self.client.post(
                reverse("admin-portal-api:token-refresh"),
                {"refreshToken": str(customer_token)},
                format="json",
            ).status_code,
            [400, 401, 403],
        )

    def test_resend_cooldown_preserves_original(self):
        original = self.challenge()
        response = self.request()
        self.assertIsNone(
            PasswordRecoveryChallenge.objects.get(
                id=response.data["challengeId"]
            ).user_id
        )
        self.assertEqual(self.confirm(original).status_code, 200)

    def test_smtp_failure_is_queued(self):
        challenge = self.challenge()
        with patch(
            "apps.accounts.recovery.send_mail", side_effect=RuntimeError("SMTP offline")
        ):
            call_command("send_password_recovery_emails", verbosity=0)
        challenge.refresh_from_db()
        self.assertEqual(challenge.delivery_attempts, 1)
        self.assertIsNone(challenge.emailed_at)
        self.assertGreater(challenge.next_delivery_at, timezone.now())
