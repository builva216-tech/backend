import base64
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import (
    AccountStatus,
    User,
    UserRole,
)
from apps.accounts.services import register_agency, register_customer
from apps.agencies.models import AgencyVerificationStatus

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
        b"%PDF-1.4\n% CarRent TN admin verification test\n",
        content_type="application/pdf",
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AdminAgencyVerificationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_tunisia_governorates", verbosity=0)

        cls.admin = User.objects.create_superuser(
            email="admin-verification@example.com",
            password="StrongAdminPassword123!",
            full_name="Verification Admin",
            phone="+21690000001",
        )

        cls.agency_user = register_agency(
            agency_name="Pending Rental Agency",
            responsible_person_name="Agency Manager",
            email="pending-agency@example.com",
            phone="+21690000002",
            password="StrongAgencyPassword123!",
            governorate_code="TN-11",
            city="Tunis",
        )

        cls.customer = register_customer(
            full_name="Regular Customer",
            email="regular-customer@example.com",
            phone="+21690000003",
            password="StrongCustomerPassword123!",
        )

    def _authenticate_admin(self):
        response = self.client.post(
            reverse("admin-portal-api:token"),
            {
                "email": self.admin.email,
                "password": "StrongAdminPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION=(f"Bearer {response.data['accessToken']}")
        )

        return response

    def _submit_agency_documents(self):
        self.client.credentials()
        self.client.force_authenticate(user=self.agency_user)

        response = self.client.post(
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

        self.assertEqual(response.status_code, 201)

        self.client.force_authenticate(user=None)
        return response

    def test_admin_login_returns_admin_session(self):
        response = self._authenticate_admin()

        self.assertEqual(response.data["user"]["role"], UserRole.ADMIN)
        self.assertIn("accessToken", response.data)
        self.assertIn("refreshToken", response.data)

    def test_customer_cannot_login_to_admin_portal(self):
        response = self.client.post(
            reverse("admin-portal-api:token"),
            {
                "email": self.customer.email,
                "password": "StrongCustomerPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_pending_agencies(self):
        self._authenticate_admin()

        response = self.client.get(
            reverse("admin-portal-api:agency-list"),
            {"status": AgencyVerificationStatus.PENDING},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["agencyName"],
            "Pending Rental Agency",
        )

    def test_admin_detail_exposes_latest_submission_contract(self):
        self._submit_agency_documents()
        self._authenticate_admin()

        agency = self.agency_user.agency_profile

        response = self.client.get(
            reverse(
                "admin-portal-api:agency-detail",
                kwargs={"agency_profile_id": agency.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["hasSubmittedDocuments"])

        submission = response.data["latestSubmission"]

        self.assertIsNotNone(submission)
        self.assertEqual(submission["attemptNumber"], 1)
        self.assertEqual(submission["status"], "pending")

        documents = submission["documents"]

        self.assertIn("businessRegistration", documents)
        self.assertIn("taxIdentification", documents)
        self.assertIn("responsibleCinRecto", documents)
        self.assertIn("responsibleCinVerso", documents)
        self.assertIn("addressProof", documents)

        # Legacy keys remain available during the RC6 -> RC7 transition.
        self.assertTrue(response.data["documentsSubmitted"])
        self.assertEqual(response.data["attemptNumber"], 1)

    def test_admin_cannot_approve_before_documents_are_submitted(self):
        self._authenticate_admin()
        agency = self.agency_user.agency_profile

        response = self.client.post(
            reverse(
                "admin-portal-api:agency-approve",
                kwargs={"agency_profile_id": agency.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_admin_can_approve_pending_agency_after_document_review(self):
        self._submit_agency_documents()
        self._authenticate_admin()

        agency = self.agency_user.agency_profile

        response = self.client.post(
            reverse(
                "admin-portal-api:agency-approve",
                kwargs={"agency_profile_id": agency.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["verificationStatus"],
            AgencyVerificationStatus.APPROVED,
        )

        agency.refresh_from_db()
        self.agency_user.refresh_from_db()

        self.assertEqual(
            agency.verification_status,
            AgencyVerificationStatus.APPROVED,
        )
        self.assertEqual(
            self.agency_user.account_status,
            AccountStatus.ACTIVE,
        )
        self.assertEqual(agency.reviewed_by_id, self.admin.id)
        self.assertIsNotNone(agency.reviewed_at)

    def test_admin_can_reject_pending_agency_with_reason(self):
        self._submit_agency_documents()
        self._authenticate_admin()

        agency = self.agency_user.agency_profile

        response = self.client.post(
            reverse(
                "admin-portal-api:agency-reject",
                kwargs={"agency_profile_id": agency.id},
            ),
            {
                "reason": "Required agency documents are incomplete.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["verificationStatus"],
            AgencyVerificationStatus.REJECTED,
        )
        self.assertEqual(
            response.data["rejectionReason"],
            "Required agency documents are incomplete.",
        )

        agency.refresh_from_db()
        self.agency_user.refresh_from_db()

        self.assertEqual(
            agency.verification_status,
            AgencyVerificationStatus.REJECTED,
        )
        self.assertEqual(
            self.agency_user.account_status,
            AccountStatus.PENDING_VERIFICATION,
        )
        self.assertEqual(agency.reviewed_by_id, self.admin.id)

    def test_customer_token_cannot_access_admin_agency_queue(self):
        token_response = self.client.post(
            reverse("accounts-api:token"),
            {
                "email": self.customer.email,
                "password": "StrongCustomerPassword123!",
            },
            format="json",
        )

        self.assertEqual(token_response.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION=(f"Bearer {token_response.data['accessToken']}")
        )

        response = self.client.get(reverse("admin-portal-api:agency-list"))

        self.assertEqual(response.status_code, 403)
