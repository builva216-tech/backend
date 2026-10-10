import base64
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import AccountStatus, User
from apps.accounts.services import register_agency
from apps.agencies.models import (
    AgencyVerificationStatus,
    AgencyVerificationSubmissionStatus,
)


VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def image(name):
    return SimpleUploadedFile(
        name,
        VALID_PNG,
        content_type="image/png",
    )


def pdf(name):
    return SimpleUploadedFile(
        name,
        b"%PDF-1.4\n% CarRent TN test\n",
        content_type="application/pdf",
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AgencyVerificationDocumentsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        call_command("seed_tunisia_governorates", verbosity=0)

        cls.admin = User.objects.create_superuser(
            email="agency-doc-admin@example.com",
            password="StrongAdminPassword123!",
            full_name="Agency Document Admin",
            phone="+21693000001",
        )
        cls.agency_user = register_agency(
            agency_name="Document Rental",
            responsible_person_name="Document Manager",
            email="agency-doc@example.com",
            phone="+21693000002",
            password="StrongAgencyPassword123!",
            governorate_code="TN-11",
            city="Tunis",
        )

    def _submit(self):
        self.client.force_authenticate(user=self.agency_user)
        return self.client.post(
            reverse("agencies-api:verification-submit"),
            {
                "businessRegistration": pdf("rne.pdf"),
                "taxIdentification": pdf("tax.pdf"),
                "responsiblePersonCinRecto": image("cin-front.png"),
                "responsiblePersonCinVerso": image("cin-back.png"),
                "addressProof": pdf("address.pdf"),
            },
            format="multipart",
        )

    def test_agency_submits_all_documents_then_admin_can_approve(self):
        response = self._submit()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["attemptNumber"], 1)

        profile = self.agency_user.agency_profile
        self.client.force_authenticate(user=self.admin)

        detail = self.client.get(
            reverse(
                "admin-portal-api:agency-detail",
                kwargs={"agency_profile_id": profile.id},
            )
        )
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.data["documentsSubmitted"])
        self.assertIsNotNone(detail.data["documents"])

        document = self.client.get(
            reverse(
                "admin-portal-api:agency-document",
                kwargs={
                    "agency_profile_id": profile.id,
                    "document_type": "responsible-person-cin-recto",
                },
            )
        )
        self.assertEqual(document.status_code, 200)
        self.assertEqual(
            document["Cache-Control"],
            "private, no-store, max-age=0",
        )

        approved = self.client.post(
            reverse(
                "admin-portal-api:agency-approve",
                kwargs={"agency_profile_id": profile.id},
            ),
            {},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)

        profile.refresh_from_db()
        self.agency_user.refresh_from_db()

        self.assertEqual(
            profile.verification_status,
            AgencyVerificationStatus.APPROVED,
        )
        self.assertEqual(
            self.agency_user.account_status,
            AccountStatus.ACTIVE,
        )
        self.assertEqual(
            profile.verification_submissions.latest(
                "submitted_at"
            ).status,
            AgencyVerificationSubmissionStatus.APPROVED,
        )

    def test_admin_cannot_approve_before_documents_are_submitted(self):
        profile = self.agency_user.agency_profile
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse(
                "admin-portal-api:agency-approve",
                kwargs={"agency_profile_id": profile.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
