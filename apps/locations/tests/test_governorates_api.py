from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase


class GovernoratesApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_tunisia_governorates", verbosity=0)

    def test_lists_all_active_governorates_in_flutter_contract_shape(self):
        response = self.client.get(
            reverse("locations-api:governorates")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 24)
        self.assertEqual(
            response.data[0],
            {
                "code": "TN-11",
                "nameAr": "تونس",
                "nameFr": "Tunis",
                "nameEn": "Tunis",
            },
        )
