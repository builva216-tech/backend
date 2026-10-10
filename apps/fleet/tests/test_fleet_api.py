import base64
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import AccountStatus
from apps.accounts.services import register_agency
from apps.agencies.models import AgencyVerificationStatus


VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FleetApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        call_command("seed_tunisia_governorates", verbosity=0)

        cls.agency_user = register_agency(
            agency_name="Fleet Agency",
            responsible_person_name="Fleet Manager",
            email="fleet-agency@example.com",
            phone="+21694000001",
            password="StrongAgencyPassword123!",
            governorate_code="TN-11",
            city="Tunis",
        )
        profile = cls.agency_user.agency_profile
        profile.verification_status = AgencyVerificationStatus.APPROVED
        profile.save(
            update_fields=["verification_status", "updated_at"]
        )
        cls.agency_user.account_status = AccountStatus.ACTIVE
        cls.agency_user.save(
            update_fields=["account_status", "updated_at"]
        )

    def test_approved_agency_creates_car_and_customer_catalog_reads_it(self):
        self.client.force_authenticate(user=self.agency_user)

        response = self.client.post(
            reverse("fleet-api:agency-cars"),
            {
                "brand": "Toyota",
                "model": "Yaris",
                "year": 2025,
                "category": "economy",
                "transmission": "automatic",
                "fuelType": "petrol",
                "seats": 5,
                "doors": 4,
                "dailyPrice": "120.000",
                "governorateCode": "TN-11",
                "city": "Tunis",
                "status": "published",
                "isAvailable": "true",
                "existingPhotoIds": "[]",
                "photos": SimpleUploadedFile(
                    "car.png",
                    VALID_PNG,
                    content_type="image/png",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "published")

        self.client.force_authenticate(user=None)
        catalog = self.client.get(
            reverse("fleet-public-api:cars")
        )
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(len(catalog.data), 1)
        self.assertEqual(catalog.data[0]["brand"], "Toyota")
