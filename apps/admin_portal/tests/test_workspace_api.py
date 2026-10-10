from datetime import timedelta

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAuditEvent, AccountStatus
from apps.accounts.services import register_agency
from apps.admin_portal.tests import test_operations_api as operations_fixtures
from apps.agencies.models import AgencyCustomerRecord, AgencyVerificationStatus
from apps.bookings.models import BookingStatus


class WorkspaceApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        operations_fixtures.AdminOperationsApiTests.setUpTestData.__func__(cls)
        cls.other_agency_user = register_agency(
            agency_name="Other Agency",
            responsible_person_name="Other Manager",
            email="other@example.com",
            phone="+21697123456",
            password="StrongAgencyPassword123!",
            governorate_code="TN-11",
            city="Tunis",
        )

    def setUp(self):
        cache.clear()

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def crm_url(self, customer=None):
        return reverse(
            "agencies-api:crm-record",
            kwargs={"customer_id": (customer or self.customer).id},
        )

    def test_crm_server_persistence_and_revision_conflict(self):
        self.auth(self.agency_user)
        response = self.client.patch(
            self.crm_url(),
            {
                "expectedRevision": 0,
                "notes": "Prefers airport pickup",
                "tags": ["VIP", "VIP"],
                "tasks": [
                    {
                        "id": "task1",
                        "title": "Check return",
                        "due": "2026-10-05",
                        "completed": False,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["revision"], 1)
        self.assertEqual(response.data["tags"], ["VIP"])
        response = self.client.patch(
            self.crm_url(),
            {"expectedRevision": 0, "notes": "Lost update"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["currentRecord"]["notes"], "Prefers airport pickup"
        )
        response = self.client.patch(
            self.crm_url(),
            {"expectedRevision": 1, "alias": "Airport guest"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notes"], "Prefers airport pickup")
        self.assertEqual(
            self.client.get(reverse("agencies-api:crm-list")).data[0]["alias"],
            "Airport guest",
        )

    def test_trial_crm_access_still_requires_existing_agency_relationship(self):
        self.auth(self.other_agency_user)
        self.assertEqual(
            self.client.get(reverse("agencies-api:crm-list")).status_code, 200
        )
        self.other_agency_user.account_status = AccountStatus.ACTIVE
        self.other_agency_user.save()
        agency = self.other_agency_user.agency_profile
        agency.verification_status = AgencyVerificationStatus.APPROVED
        agency.save()
        self.assertEqual(
            self.client.patch(
                self.crm_url(),
                {"expectedRevision": 0, "notes": "Forbidden"},
                format="json",
            ).status_code,
            404,
        )
        self.assertFalse(AgencyCustomerRecord.objects.exists())

    def test_crm_rejects_duplicate_tasks_oversize_notes_and_unknown_labels(self):
        self.auth(self.agency_user)
        task = {"id": "one", "title": "Call", "due": "2026-10-05"}
        for values in [
            {"notes": "x" * 4001},
            {"tags": ["Unknown"]},
            {"tasks": [task, task]},
            {"tasks": [{**task, "due": "2200-01-01"}]},
        ]:
            self.assertEqual(
                self.client.patch(
                    self.crm_url(), {"expectedRevision": 0, **values}, format="json"
                ).status_code,
                400,
            )
        self.assertFalse(AgencyCustomerRecord.objects.exists())

    def test_customer_summary_real_name_and_contact_status_gate(self):
        self.auth(self.agency_user)
        response = self.client.get(
            reverse(
                "bookings-api:agency-customer-summary",
                kwargs={"booking_id": self.booking.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["displayName"], self.customer.full_name)
        url = reverse(
            "bookings-api:agency-customer-contact",
            kwargs={"booking_id": self.booking.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.data["access"], "locked")
        self.assertIsNone(response.data["phone"])
        self.booking.status = BookingStatus.APPROVED
        self.booking.save()
        response = self.client.get(url)
        self.assertEqual(response.data["phone"], self.customer.phone)
        self.auth(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_accounts_search_and_access_audit(self):
        self.auth(self.admin)
        response = self.client.get(
            reverse("admin-portal-api:accounts"),
            {"role": "agency", "q": "Other Agency"},
        )
        self.assertEqual(response.status_code, 200)
        # Name search uses responsible person; email query works for all roles.
        response = self.client.get(
            reverse("admin-portal-api:accounts"), {"q": "other@example.com"}
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["verificationStage"], "notSubmitted"
        )
        url = reverse(
            "admin-portal-api:account-access", kwargs={"user_id": self.customer.id}
        )
        self.assertEqual(
            self.client.patch(
                url,
                {"isActive": False, "reason": "Support investigation"},
                format="json",
            ).status_code,
            200,
        )
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertTrue(
            AccountAuditEvent.objects.filter(
                subject=self.customer, actor=self.admin, action="account_suspended"
            ).exists()
        )
        self.assertEqual(
            self.client.patch(
                url,
                {"isActive": True, "reason": "Investigation complete"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("admin-portal-api:audit")).data["count"], 2
        )

    def test_admin_cannot_suspend_self_or_bypass_activation(self):
        self.auth(self.admin)
        url = reverse(
            "admin-portal-api:account-access", kwargs={"user_id": self.admin.id}
        )
        self.assertEqual(
            self.client.patch(
                url, {"isActive": False, "reason": "Lock account"}, format="json"
            ).status_code,
            400,
        )
        url = reverse(
            "admin-portal-api:account-access",
            kwargs={"user_id": self.other_agency_user.id},
        )
        self.assertEqual(
            self.client.patch(
                url, {"isActive": True, "reason": "Restore login"}, format="json"
            ).status_code,
            200,
        )
        self.other_agency_user.refresh_from_db()
        self.assertEqual(
            self.other_agency_user.account_status, AccountStatus.PENDING_VERIFICATION
        )
        self.auth(self.customer)
        self.assertEqual(
            self.client.get(reverse("admin-portal-api:accounts")).status_code, 403
        )

    def test_analytics_collection_dates_deposit_separation_and_pending_onboarding(self):
        self.auth(self.admin)
        self.payment.status = "paid"
        self.payment.paid_at = timezone.now()
        self.payment.save()
        response = self.client.get(reverse("admin-portal-api:analytics"), {"days": 7})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["rentalCollections"]), 240)
        self.assertEqual(float(response.data["paidDepositRecords"]), 300)
        self.assertEqual(
            sum(
                float(bucket["rentalCollections"])
                for bucket in response.data["buckets"]
            ),
            240,
        )
        self.assertEqual(
            sum(bucket["requests"] for bucket in response.data["buckets"]),
            response.data["requests"],
        )
        self.assertEqual(response.data["agenciesAwaitingDocuments"], 1)
        self.payment.paid_at = timezone.now() - timedelta(days=8)
        self.payment.save()
        self.assertEqual(
            float(
                self.client.get(
                    reverse("admin-portal-api:analytics"), {"days": 7}
                ).data["rentalCollections"]
            ),
            0,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin-portal-api:analytics"), {"days": 5}
            ).status_code,
            400,
        )

    def test_suspension_revokes_sessions_even_after_reactivation(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.customer)
        refresh["sessionVersion"] = self.customer.session_version
        access = str(refresh.access_token)
        self.auth(self.admin)
        url = reverse(
            "admin-portal-api:account-access", kwargs={"user_id": self.customer.id}
        )
        self.assertEqual(
            self.client.patch(
                url,
                {"isActive": False, "reason": "Support investigation"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(
                url,
                {"isActive": True, "reason": "Investigation complete"},
                format="json",
            ).status_code,
            200,
        )
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access)
        self.assertEqual(self.client.get(reverse("accounts-api:me")).status_code, 401)
        self.client.credentials()
        self.assertEqual(
            self.client.post(
                reverse("accounts-api:token-refresh"),
                {"refreshToken": str(refresh)},
                format="json",
            ).status_code,
            401,
        )

    def test_pending_review_filter_distinguishes_unsubmitted_accounts(self):
        self.auth(self.admin)
        response = self.client.get(
            reverse("admin-portal-api:agency-list"),
            {"status": "pending", "submittedOnly": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(
            self.client.get(reverse("admin-portal-api:overview")).data[
                "pendingAgencies"
            ],
            0,
        )

    def test_crm_rejects_stale_account_context_even_with_customer_relationship(self):
        self.auth(self.agency_user)
        response = self.client.patch(
            self.crm_url(),
            {
                "agencyId": str(self.other_agency_user.id),
                "expectedRevision": 0,
                "notes": "Wrong session context",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(AgencyCustomerRecord.objects.exists())
