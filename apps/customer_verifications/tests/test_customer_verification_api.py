import base64
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import register_customer

from apps.customer_verifications.models import (
    CustomerVerificationStatus,
)


# 1x1 valid PNG.
VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def image(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        VALID_PNG,
        content_type="image/png",
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CustomerVerificationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="customer-review-admin@example.com",
            password="StrongAdminPassword123!",
            full_name="Customer Review Admin",
            phone="+21691000001",
        )

        cls.customer = register_customer(
            full_name="Verification Customer",
            email="verification-customer@example.com",
            phone="+21691000002",
            password="StrongCustomerPassword123!",
        )

        cls.other_customer = register_customer(
            full_name="Other Customer",
            email="other-verification-customer@example.com",
            phone="+21691000003",
            password="StrongCustomerPassword123!",
        )

    def _submit(self, user=None):
        self.client.force_authenticate(
            user=user or self.customer,
        )

        return self.client.post(
            reverse("customer-verification-api:submit"),
            {
                "cinRecto": image("cin_recto.png"),
                "cinVerso": image("cin_verso.png"),
                "selfie": image("selfie.png"),
            },
            format="multipart",
        )

    def test_customer_can_submit_three_required_images(self):
        response = self._submit()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["attemptNumber"], 1)
        self.assertEqual(
            response.data["status"],
            CustomerVerificationStatus.PENDING,
        )

    def test_customer_cannot_create_second_pending_submission(self):
        first = self._submit()
        self.assertEqual(first.status_code, 201)

        second = self._submit()

        self.assertEqual(second.status_code, 409)

    def test_customer_can_read_latest_status(self):
        self._submit()

        self.client.force_authenticate(user=self.customer)

        response = self.client.get(
            reverse("customer-verification-api:me")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["verification"]["status"],
            CustomerVerificationStatus.PENDING,
        )

    def test_admin_can_list_and_approve_pending_customer(self):
        submit_response = self._submit()
        submission_id = submit_response.data["submissionId"]

        self.client.force_authenticate(user=self.admin)

        list_response = self.client.get(
            reverse("admin-customer-verification-api:list"),
            {"status": "pending"},
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)

        approve_response = self.client.post(
            reverse(
                "admin-customer-verification-api:approve",
                kwargs={"submission_id": submission_id},
            ),
            {},
            format="json",
        )

        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(
            approve_response.data["status"],
            CustomerVerificationStatus.APPROVED,
        )
        self.assertEqual(
            approve_response.data["reviewedBy"]["id"],
            str(self.admin.id),
        )

    def test_admin_can_reject_and_customer_can_resubmit(self):
        submit_response = self._submit()
        submission_id = submit_response.data["submissionId"]

        self.client.force_authenticate(user=self.admin)

        reject_response = self.client.post(
            reverse(
                "admin-customer-verification-api:reject",
                kwargs={"submission_id": submission_id},
            ),
            {"reason": "CIN image is not readable."},
            format="json",
        )

        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(
            reject_response.data["status"],
            CustomerVerificationStatus.REJECTED,
        )

        second = self._submit()
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["attemptNumber"], 2)

    def test_customer_cannot_read_protected_document_endpoint(self):
        submit_response = self._submit()
        submission_id = submit_response.data["submissionId"]

        self.client.force_authenticate(user=self.other_customer)

        response = self.client.get(
            reverse(
                "admin-customer-verification-api:document",
                kwargs={
                    "submission_id": submission_id,
                    "document_type": "cin-recto",
                },
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_read_protected_document_endpoint(self):
        submit_response = self._submit()
        submission_id = submit_response.data["submissionId"]

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                "admin-customer-verification-api:document",
                kwargs={
                    "submission_id": submission_id,
                    "document_type": "selfie",
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Cache-Control"],
            "private, no-store, max-age=0",
        )
