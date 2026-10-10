import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APITestCase

from apps.admin_portal.tests import test_operations_api as fixtures


class AgencyProfileEditingApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AdminOperationsApiTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.settings = override_settings(MEDIA_ROOT=self.directory)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.client.force_authenticate(self.agency_user)
        self.url = reverse("agencies-api:me")

    def test_edit_is_published_and_stale_revision_is_rejected(self):
        old = self.client.get(self.url).data["updatedAt"]
        response = self.client.patch(
            self.url,
            {
                "agencyName": "Airport Rentals",
                "bio": "Airport collection and delivery",
                "governorateCode": "TN-12",
                "expectedUpdatedAt": old,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["governorateCode"], "TN-12")
        public = self.client.get(
            reverse(
                "agencies-api:public-profile", kwargs={"agency_id": self.agency_user.id}
            )
        )
        self.assertEqual(public.data["displayName"], "Airport Rentals")
        self.assertEqual(public.data["bio"], "Airport collection and delivery")
        self.assertEqual(
            self.client.patch(
                self.url,
                {"bio": "Stale overwrite", "expectedUpdatedAt": old},
                format="json",
            ).status_code,
            409,
        )
        self.agency.refresh_from_db()
        self.assertEqual(self.agency.bio, "Airport collection and delivery")

    def test_profile_fields_validate_instead_of_silent_truncation(self):
        for values in [
            {"city": "x" * 81},
            {"bio": "x" * 501},
            {"services": ["Airport", "airport"]},
            {"governorateCode": "XX-00"},
        ]:
            self.assertEqual(
                self.client.patch(self.url, values, format="json").status_code, 400
            )
        self.agency.refresh_from_db()
        self.assertEqual(self.agency.city, "Tunis")

    def test_pending_agency_can_prepare_private_profile_during_trial(self):
        self.agency_user.account_status = "pendingVerification"
        self.agency_user.save()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(
            self.client.patch(
                self.url, {"bio": "Prepare listing during trial"}, format="json"
            ).status_code,
            200,
        )

        public = self.client.get(reverse('agencies-api:public-profile', kwargs={'agency_id': self.agency_user.id}))
        self.assertEqual(public.status_code, 404)

    def test_image_upload_read_and_removal(self):
        stream = io.BytesIO()
        Image.new("RGB", (10, 10)).save(stream, format="PNG")
        image = SimpleUploadedFile(
            "profile.png", stream.getvalue(), content_type="image/png"
        )
        response = self.client.patch(
            self.url, {"profileImage": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["profileImage"])
        url = reverse(
            "agencies-api:profile-image", kwargs={"agency_id": self.agency_user.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(
            self.client.patch(
                self.url, {"removeProfileImage": True}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_image_upload_is_rejected(self):
        image = SimpleUploadedFile(
            "profile.png", b"Not actually an image", content_type="image/png"
        )
        self.assertEqual(
            self.client.patch(
                self.url, {"profileImage": image}, format="multipart"
            ).status_code,
            400,
        )

    def test_profile_update_rejects_wrong_account_context(self):
        self.assertEqual(
            self.client.patch(
                self.url,
                {"agencyId": str(self.customer.id), "bio": "Wrong account"},
                format="json",
            ).status_code,
            404,
        )

    def test_image_mime_matches_detected_format(self):
        stream = io.BytesIO()
        Image.new("RGB", (10, 10)).save(stream, format="PNG")
        image = SimpleUploadedFile(
            "portrait.jpg", stream.getvalue(), content_type="image/jpeg"
        )
        self.assertEqual(
            self.client.patch(
                self.url, {"profileImage": image}, format="multipart"
            ).status_code,
            200,
        )
        response = self.client.get(
            reverse(
                "agencies-api:profile-image", kwargs={"agency_id": self.agency_user.id}
            )
        )
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_public_verification_flag_is_backend_derived_and_not_editable(self):
        url = reverse(
            "agencies-api:public-profile", kwargs={"agency_id": self.agency_user.id}
        )
        self.assertTrue(self.client.get(url).data["isVerified"])
        self.client.patch(self.url, {"isVerified": False}, format="json")
        self.assertTrue(self.client.get(url).data["isVerified"])
