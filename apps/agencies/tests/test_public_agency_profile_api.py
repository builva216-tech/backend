from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import AccountStatus
from apps.accounts.services import register_agency
from apps.agencies.models import AgencyVerificationStatus


class PublicAgencyProfileApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "seed_tunisia_governorates",
            verbosity=0,
        )

        cls.approved_user = register_agency(
            agency_name="Public Rental Agency",
            responsible_person_name="Private Manager Name",
            email="public-agency@example.com",
            phone="+21692000001",
            password="StrongAgencyPassword123!",
            governorate_code="TN-23",
            city="Menzel Bourguiba",
        )

        approved_profile = cls.approved_user.agency_profile
        approved_profile.verification_status = (
            AgencyVerificationStatus.APPROVED
        )
        approved_profile.save(
            update_fields=[
                "verification_status",
                "updated_at",
            ]
        )

        cls.approved_user.account_status = AccountStatus.ACTIVE
        cls.approved_user.save(
            update_fields=[
                "account_status",
                "updated_at",
            ]
        )

        cls.pending_user = register_agency(
            agency_name="Pending Rental Agency",
            responsible_person_name="Pending Manager",
            email="pending-public-agency@example.com",
            phone="+21692000002",
            password="StrongAgencyPassword123!",
            governorate_code="TN-11",
            city="Tunis",
        )

    def test_public_endpoint_returns_only_safe_approved_profile_fields(self):
        response = self.client.get(
            reverse(
                "agencies-api:public-profile",
                kwargs={
                    "agency_id": self.approved_user.id,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["agencyId"],
            str(self.approved_user.id),
        )
        self.assertEqual(
            response.data["displayName"],
            "Public Rental Agency",
        )
        self.assertEqual(
            response.data["governorateCode"],
            "TN-23",
        )
        self.assertEqual(
            response.data["city"],
            "Menzel Bourguiba",
        )

        self.assertNotIn("email", response.data)
        self.assertNotIn("phone", response.data)
        self.assertNotIn(
            "responsiblePersonName",
            response.data,
        )

    def test_pending_agency_is_not_public(self):
        response = self.client.get(
            reverse(
                "agencies-api:public-profile",
                kwargs={
                    "agency_id": self.pending_user.id,
                },
            )
        )

        self.assertEqual(response.status_code, 404)
