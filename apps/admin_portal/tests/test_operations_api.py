from datetime import timedelta

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import AccountStatus, User
from apps.accounts.services import register_agency, register_customer
from apps.agencies.models import AgencyVerificationStatus
from apps.bookings.models import Booking, BookingStatus
from apps.fleet.models import (
    Car,
    CarCategory,
    CarFuelType,
    CarStatus,
    CarTransmission,
)
from apps.locations.models import Governorate
from apps.payments.models import Payment, PaymentStatus


class AdminOperationsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_tunisia_governorates", verbosity=0)

        cls.admin = User.objects.create_superuser(
            email="operations-admin@example.com",
            password="StrongAdminPassword123!",
            full_name="Operations Admin",
            phone="+21697000001",
        )

        cls.agency_user = register_agency(
            agency_name="Operations Agency",
            responsible_person_name="Operations Manager",
            email="operations-agency@example.com",
            phone="+21697000002",
            password="StrongAgencyPassword123!",
            governorate_code="TN-11",
            city="Tunis",
        )
        cls.agency = cls.agency_user.agency_profile
        cls.agency.verification_status = (
            AgencyVerificationStatus.APPROVED
        )
        cls.agency.save(
            update_fields=[
                "verification_status",
                "updated_at",
            ]
        )

        cls.agency_user.account_status = AccountStatus.ACTIVE
        cls.agency_user.save(
            update_fields=[
                "account_status",
                "updated_at",
            ]
        )

        cls.customer = register_customer(
            full_name="Operations Customer",
            email="operations-customer@example.com",
            phone="+21697000003",
            password="StrongCustomerPassword123!",
        )

        governorate = Governorate.objects.get(code="TN-11")

        cls.car = Car.objects.create(
            agency=cls.agency,
            brand="Toyota",
            model="Yaris",
            year=2025,
            category=CarCategory.ECONOMY,
            transmission=CarTransmission.AUTOMATIC,
            fuel_type=CarFuelType.PETROL,
            seats=5,
            doors=4,
            plate_number="123 TUN 4567",
            daily_price="120.000",
            governorate=governorate,
            city="Tunis",
            status=CarStatus.PUBLISHED,
            is_available=True,
        )

        pickup = timezone.now() + timedelta(days=3)
        returned = pickup + timedelta(days=2)

        cls.booking = Booking.objects.create(
            car=cls.car,
            agency=cls.agency,
            customer=cls.customer,
            pickup_at=pickup,
            return_at=returned,
            rental_days=2,
            daily_price_snapshot="120.000",
            base_price="240.000",
            extras_total="0.000",
            insurance_total="0.000",
            total_price="240.000",
            security_deposit="300.000",
            pickup_governorate=governorate,
            pickup_city="Tunis",
            payment_method="cash",
            status=BookingStatus.REQUESTED,
        )

        cls.payment = Payment.objects.create(
            booking=cls.booking,
            method="cash",
            status=PaymentStatus.DUE,
            rental_amount="240.000",
            deposit_amount="300.000",
            invoice_number="INV-TEST-0001",
        )

    def setUp(self):
        self.client.force_authenticate(user=self.admin)

    def test_admin_overview_returns_live_operational_counts(self):
        response = self.client.get(
            reverse("admin-portal-api:overview")
        )

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["activeCars"], 1)
        self.assertGreaterEqual(
            response.data["requestedBookings"],
            1,
        )
        self.assertGreaterEqual(response.data["paymentsDue"], 1)

    def test_admin_cars_endpoint_exposes_admin_only_plate_number(self):
        response = self.client.get(
            reverse("admin-portal-api:cars")
        )

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        item = next(
            value
            for value in response.data
            if value["id"] == str(self.car.id)
        )
        self.assertEqual(item["plateNumber"], "123 TUN 4567")

    def test_admin_bookings_endpoint_returns_booking_context(self):
        response = self.client.get(
            reverse("admin-portal-api:bookings")
        )

        self.assertEqual(response.status_code, 200)
        item = next(
            value
            for value in response.data
            if value["id"] == str(self.booking.id)
        )
        self.assertEqual(item["status"], BookingStatus.REQUESTED)
        self.assertEqual(
            item["agency"]["agencyName"],
            "Operations Agency",
        )
        self.assertEqual(
            item["customer"]["fullName"],
            "Operations Customer",
        )

    def test_admin_payments_endpoint_returns_cash_record(self):
        response = self.client.get(
            reverse("admin-portal-api:payments")
        )

        self.assertEqual(response.status_code, 200)
        item = next(
            value
            for value in response.data
            if value["id"] == str(self.payment.id)
        )
        self.assertEqual(item["status"], PaymentStatus.DUE)
        self.assertEqual(item["invoiceNumber"], "INV-TEST-0001")
