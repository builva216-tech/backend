from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAgency
from apps.bookings.models import Booking, BookingStatus
from apps.customer_verifications.models import CustomerVerificationSubmission
from apps.fleet.services import require_approved_agency
from apps.profiles.models import CustomerProfile


class AgencyCustomerSummaryView(APIView):
    permission_classes = (IsAgency,)

    def get(self, request, booking_id):
        agency = require_approved_agency(request.user)
        booking = get_object_or_404(
            Booking.objects.select_related("customer"), id=booking_id, agency=agency
        )
        profile = CustomerProfile.objects.filter(user=booking.customer).first()
        latest = (
            CustomerVerificationSubmission.objects.filter(user=booking.customer)
            .order_by("-attempt_number")
            .first()
        )
        return Response(
            {
                "customerId": str(booking.customer_id),
                "displayName": booking.customer.full_name,
                "city": profile.city if profile else "",
                "isIdentityVerified": bool(latest and latest.status == "approved"),
            }
        )


class AgencyCustomerContactView(APIView):
    permission_classes = (IsAgency,)

    def get(self, request, booking_id):
        agency = require_approved_agency(request.user)
        booking = get_object_or_404(Booking, id=booking_id, agency=agency)
        unlocked = booking.status in [
            BookingStatus.APPROVED,
            BookingStatus.CONFIRMED,
            BookingStatus.ACTIVE,
            BookingStatus.COMPLETED,
        ]
        return Response(
            {
                "bookingId": str(booking.id),
                "customerId": str(booking.customer_id),
                "access": "available" if unlocked else "locked",
                "phone": booking.customer.phone if unlocked else None,
                "message": "Customer contact is available for this booking."
                if unlocked
                else "Approve this request before accessing customer contact details.",
            }
        )
