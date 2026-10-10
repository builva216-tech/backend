from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase


class CurrentAgencyProfileApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_tunisia_governorates", verbosity=0)

    def test_registered_agency_can_read_its_profile(self):
        register_response = self.client.post(
            reverse("accounts-api:register-agency"),
            {
                "agencyName": "La Marsa Rent",
                "responsiblePersonName": "Agency Manager",
                "email": "agency-profile@example.com",
                "phone": "+21620222334",
                "password": "StrongPassword123!",
                "governorateCode": "TN-11",
                "city": "La Marsa",
            },
            format="json",
        )

        self.assertEqual(register_response.status_code, 201)

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {register_response.data['accessToken']}"
            )
        )

        profile_response = self.client.get(
            reverse("agencies-api:me")
        )

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(
            profile_response.data["governorateCode"],
            "TN-11",
        )
        self.assertEqual(
            profile_response.data["city"],
            "La Marsa",
        )
        self.assertEqual(
            profile_response.data["fleetSize"],
            0,
        )
