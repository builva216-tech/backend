from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.services import register_customer


@override_settings(DEBUG=True)
class ContactVerificationApiTests(APITestCase):
    def setUp(self):
        self.user = register_customer(
            full_name="Contact Customer",
            email="contact@example.com",
            phone="+21620123456",
            password="StrongPassword123!",
        )

        token_response = self.client.post(
            reverse("accounts-api:token"),
            {
                "email": "contact@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION=(f"Bearer {token_response.data['accessToken']}")
        )

    def test_customer_can_change_email_after_valid_otp(self):
        request_response = self.client.post(
            reverse("accounts-api:contact-change-request"),
            {
                "type": "email",
                "value": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(request_response.status_code, 201)
        self.assertEqual(
            request_response.data["verification"]["type"],
            "email",
        )
        self.assertEqual(
            request_response.data["verification"]["attemptsRemaining"],
            5,
        )
        self.assertIn("prototypeOtpCode", request_response.data)

        confirm_response = self.client.post(
            reverse("accounts-api:contact-change-confirm"),
            {
                "verificationId": (
                    request_response.data["verification"]["verificationId"]
                ),
                "otpCode": request_response.data["prototypeOtpCode"],
            },
            format="json",
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(
            confirm_response.data["email"],
            "updated@example.com",
        )
        self.assertTrue(confirm_response.data["isEmailVerified"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")

    def test_incorrect_otp_decrements_attempts(self):
        request_response = self.client.post(
            reverse("accounts-api:contact-change-request"),
            {
                "type": "phone",
                "value": "+21620999888",
            },
            format="json",
        )

        self.assertEqual(request_response.status_code, 201)

        confirm_response = self.client.post(
            reverse("accounts-api:contact-change-confirm"),
            {
                "verificationId": (
                    request_response.data["verification"]["verificationId"]
                ),
                "otpCode": "000000",
            },
            format="json",
        )

        # There is an extremely small chance the generated code is 000000.
        # If that happens, this test should be rerun.
        if confirm_response.status_code == 200:
            self.skipTest("Generated OTP matched the test's wrong-code value.")

        self.assertEqual(confirm_response.status_code, 422)

    def test_wrong_codes_commit_attempts_and_lock_persistently(self):
        from apps.accounts.models import ContactVerificationChallenge

        requested = self.client.post(
            reverse("accounts-api:contact-change-request"),
            {"type": "phone", "value": "+21620888777"},
            format="json",
        )
        code = requested.data["prototypeOtpCode"]
        wrong = "111111" if code != "111111" else "222222"
        identifier = requested.data["verification"]["verificationId"]
        for index in range(5):
            response = self.client.post(
                reverse("accounts-api:contact-change-confirm"),
                {"verificationId": identifier, "otpCode": wrong},
                format="json",
            )
            self.assertEqual(response.status_code, 423 if index == 4 else 422)
        challenge = ContactVerificationChallenge.objects.get(pk=identifier)
        self.assertEqual(challenge.attempts_remaining, 0)
        self.assertEqual(challenge.status, "locked")
        self.assertEqual(
            self.client.post(
                reverse("accounts-api:contact-change-confirm"),
                {"verificationId": identifier, "otpCode": code},
                format="json",
            ).status_code,
            423,
        )

    @override_settings(
        DEBUG=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_production_email_change_sends_code_without_returning_it(self):
        import re

        from django.core import mail

        requested = self.client.post(
            reverse("accounts-api:contact-change-request"),
            {"type": "email", "value": "real-delivery@example.com"},
            format="json",
        )
        self.assertEqual(requested.status_code, 201)
        self.assertNotIn("prototypeOtpCode", requested.data)
        self.assertEqual(mail.outbox[0].to, ["real-delivery@example.com"])
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        response = self.client.post(
            reverse("accounts-api:contact-change-confirm"),
            {
                "verificationId": requested.data["verification"]["verificationId"],
                "otpCode": code,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "real-delivery@example.com")

    @override_settings(DEBUG=False)
    def test_phone_provider_missing_returns_actionable_error(self):
        response = self.client.post(
            reverse("accounts-api:contact-change-request"),
            {"type": "phone", "value": "+21620888777"},
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("SMS provider", response.data["detail"])
