from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import AccountStatus, User, UserRole


class AuthApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_tunisia_governorates", verbosity=0)

    def test_customer_registration_matches_flutter_session_contract(self):
        response = self.client.post(
            reverse("accounts-api:register-customer"),
            {
                "fullName": "Demo Customer",
                "email": "customer@example.com",
                "phone": "+21620111222",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "customer")
        self.assertIn("accessToken", response.data)
        self.assertIn("refreshToken", response.data)

    def test_agency_registration_persists_governorate_code_and_optional_city(self):
        response = self.client.post(
            reverse("accounts-api:register-agency"),
            {
                "agencyName": "La Marsa Rent",
                "responsiblePersonName": "Agency Manager",
                "email": "agency@example.com",
                "phone": "+21620222333",
                "password": "StrongPassword123!",
                "governorateCode": "TN-11",
                "city": "La Marsa",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="agency@example.com")
        self.assertEqual(user.role, UserRole.AGENCY)
        self.assertEqual(
            user.account_status,
            AccountStatus.PENDING_VERIFICATION,
        )
        self.assertEqual(user.agency_profile.governorate_id, "TN-11")
        self.assertEqual(user.agency_profile.city, "La Marsa")

    def test_admin_cannot_use_mobile_login_endpoint(self):
        User.objects.create_superuser(
            email="admin@example.com",
            full_name="Admin",
            phone="+21620333444",
            password="StrongPassword123!",
        )

        response = self.client.post(
            reverse("accounts-api:token"),
            {
                "email": "admin@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
