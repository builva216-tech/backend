import base64
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import AccountStatus, User
from apps.accounts.services import register_agency, register_customer
from apps.agencies.models import AgencyVerificationStatus
from apps.customer_verifications.models import (
    CustomerVerificationStatus,
    CustomerVerificationSubmission,
)
from apps.fleet.models import (
    Car,
    CarCategory,
    CarFuelType,
    CarPhoto,
    CarStatus,
    CarTransmission,
)
from apps.locations.models import Governorate


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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BookingLifecycleApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        call_command("seed_tunisia_governorates", verbosity=0)
        governorate = Governorate.objects.get(code="TN-11")

        cls.agency_user = register_agency(
            agency_name="Booking Agency",
            responsible_person_name="Booking Manager",
            email="booking-agency@example.com",
            phone="+21695000001",
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

        cls.customer = register_customer(
            full_name="Verified Customer",
            email="verified-booking@example.com",
            phone="+21695000002",
            password="StrongCustomerPassword123!",
        )
        CustomerVerificationSubmission.objects.create(
            user=cls.customer,
            attempt_number=1,
            status=CustomerVerificationStatus.APPROVED,
            cin_recto=image("front.png"),
            cin_verso=image("back.png"),
            selfie=image("selfie.png"),
        )

        cls.unverified_customer = register_customer(
            full_name="Unverified Customer",
            email="unverified-booking@example.com",
            phone="+21695000003",
            password="StrongCustomerPassword123!",
        )

        cls.car = Car.objects.create(
            agency=profile,
            brand="Kia",
            model="Rio",
            year=2024,
            category=CarCategory.ECONOMY,
            transmission=CarTransmission.AUTOMATIC,
            fuel_type=CarFuelType.PETROL,
            seats=5,
            doors=4,
            daily_price="100.000",
            governorate=governorate,
            city="Tunis",
            status=CarStatus.PUBLISHED,
            is_available=True,
        )
        CarPhoto.objects.create(
            car=cls.car,
            image=image("car.png"),
            position=0,
        )

    def _period(self):
        pickup = timezone.now() + timedelta(days=2)
        return pickup, pickup + timedelta(hours=25)

    def test_booking_requires_approved_customer_kyc(self):
        pickup, returned = self._period()
        self.client.force_authenticate(user=self.unverified_customer)

        response = self.client.post(
            reverse("bookings-api:customer-list-create"),
            {
                "carId": str(self.car.id),
                "pickupDate": pickup.isoformat(),
                "returnDate": returned.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_saved_request_survives_new_session_and_is_visible_to_agency(self):
        from rest_framework.test import APIClient
        from apps.notifications.models import Notification
        pickup, returned = self._period()
        self.client.force_authenticate(user=self.customer)
        created = self.client.post(reverse('bookings-api:customer-list-create'), {
            'carId': str(self.car.pk), 'pickupDate': pickup.isoformat(), 'returnDate': returned.isoformat(),
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        booking_id = created.data['id']
        fresh = APIClient()
        fresh.force_authenticate(user=self.customer)
        listed = fresh.get(reverse('bookings-api:customer-list-create'))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([b['id'] for b in listed.data if b['status'] == 'requested'], [booking_id])
        self.assertIn('no-store', listed['Cache-Control'])
        self.assertIn('Authorization', listed['Vary'])
        detail = fresh.get(reverse('bookings-api:customer-detail', kwargs={'booking_id': booking_id}))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['id'], booking_id)
        fresh.force_authenticate(user=self.agency_user)
        agency = fresh.get(reverse('bookings-api:agency-list'))
        self.assertIn(booking_id, [b['id'] for b in agency.data])
        self.assertEqual(Notification.objects.filter(booking_id=booking_id).count(), 2)
        fresh.force_authenticate(user=self.unverified_customer)
        self.assertEqual(fresh.get(reverse('bookings-api:customer-list-create')).data, [])
        self.assertEqual(fresh.get(reverse('bookings-api:customer-detail', kwargs={'booking_id': booking_id})).status_code, 404)

    def test_verified_customer_booking_can_complete_lifecycle(self):
        self._complete_lifecycle(expire_after_approval=False)

    def test_expired_trial_can_finish_previously_approved_rental(self):
        self._complete_lifecycle(expire_after_approval=True)

    def _complete_lifecycle(self, *, expire_after_approval):
        pickup, returned = self._period()
        self.client.force_authenticate(user=self.customer)

        created = self.client.post(
            reverse("bookings-api:customer-list-create"),
            {
                "carId": str(self.car.id),
                "pickupDate": pickup.isoformat(),
                "returnDate": returned.isoformat(),
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["totalDays"], 2)
        booking_id = created.data["id"]

        self.client.force_authenticate(user=self.agency_user)
        approved = self.client.post(
            reverse(
                "bookings-api:agency-approve",
                kwargs={"booking_id": booking_id},
            ),
            {},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], "approved")
        self.assertIsNotNone(approved.data["payment"])
        payment_id = approved.data["payment"]["id"]

        if expire_after_approval:
            from apps.agencies.models import AgencyProfile
            from apps.bookings.models import Booking
            now = timezone.now()
            AgencyProfile.objects.filter(user=self.agency_user).update(created_at=now-timedelta(days=15))
            Booking.objects.filter(pk=booking_id).update(
                created_at=now-timedelta(days=3),
                agency_responded_at=now-timedelta(days=2),
            )
            self.assertFalse(self.client.get('/api/v1/agencies/subscription/').data['canManage'])
            self.assertEqual(self.client.post('/api/v1/fleet/cars/', {}, format='json').status_code, 403)

        paid = self.client.post(
            reverse(
                "payments-api:agency-mark-paid",
                kwargs={"payment_id": payment_id},
            ),
            {},
            format="json",
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.data["status"], "paid")

        self.client.force_authenticate(user=self.customer)
        confirmed = self.client.post(
            reverse(
                "bookings-api:customer-confirm",
                kwargs={"booking_id": booking_id},
            ),
            {},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["status"], "confirmed")

        self.client.force_authenticate(user=self.agency_user)
        active = self.client.post(
            reverse(
                "bookings-api:agency-pickup",
                kwargs={"booking_id": booking_id},
            ),
            {},
            format="json",
        )
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.data["status"], "active")

        completed = self.client.post(
            reverse(
                "bookings-api:agency-return",
                kwargs={"booking_id": booking_id},
            ),
            {},
            format="json",
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data["status"], "completed")
