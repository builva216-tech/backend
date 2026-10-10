from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.fleet.models import Car

from ..models import Booking
from ..services import (
    agency_transition,
    calculate_quote,
    create_booking,
    customer_cancel,
    customer_confirm,
    require_agency,
    require_customer,
)
from .serializers import (
    BookingAgencyActionSerializer,
    BookingCreateSerializer,
    BookingQuoteSerializer,
    BookingRejectSerializer,
    BookingSerializer,
)


def _booking_queryset():
    return (
        Booking.objects.select_related(
            "car",
            "agency",
            "agency__user",
            "customer",
            "pickup_governorate",
            "payment",
        )
        .prefetch_related("extras")
    )


class BookingQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        require_customer(request.user)
        serializer = BookingQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        car = get_object_or_404(
            Car.objects.select_related(
                "agency",
                "agency__user",
                "governorate",
            ),
            pk=data["carId"],
        )

        quote = calculate_quote(
            car=car,
            pickup_at=data["pickupDate"],
            return_at=data["returnDate"],
            extra_ids=data.get("extraIds", []),
            insurance_id=data.get("insuranceId"),
        )

        return Response(
            {
                "rentalDays": quote["rental_days"],
                "dailyPrice": float(quote["daily_price"]),
                "basePrice": float(quote["base_price"]),
                "extrasTotal": float(quote["extras_total"]),
                "insuranceTotal": float(
                    quote["insurance_total"]
                ),
                "totalPrice": float(quote["total_price"]),
                "securityDeposit": float(
                    quote["security_deposit"]
                ),
                "paymentMethod": "cash",
            }
        )


class CustomerBookingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        require_customer(request.user)
        queryset = _booking_queryset().filter(
            customer=request.user
        )
        return Response(
            BookingSerializer(queryset, many=True).data
        )

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = create_booking(
            user=request.user,
            car_id=data["carId"],
            pickup_at=data["pickupDate"],
            return_at=data["returnDate"],
            extra_ids=data.get("extraIds", []),
            insurance_id=data.get("insuranceId"),
            customer_note=data.get("customerNote", ""),
        )

        booking = _booking_queryset().get(pk=booking.id)

        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        require_customer(request.user)
        booking = get_object_or_404(
            _booking_queryset(),
            pk=booking_id,
            customer=request.user,
        )
        return Response(BookingSerializer(booking).data)


class CustomerBookingConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = customer_confirm(
            user=request.user,
            booking_id=booking_id,
        )
        booking = _booking_queryset().get(pk=booking.id)
        return Response(BookingSerializer(booking).data)


class CustomerBookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = customer_cancel(
            user=request.user,
            booking_id=booking_id,
        )
        booking = _booking_queryset().get(pk=booking.id)
        return Response(BookingSerializer(booking).data)


class AgencyBookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = require_agency(request.user)
        queryset = _booking_queryset().filter(agency=profile)
        requested_status = request.query_params.get(
            "status",
            "",
        ).strip()
        if requested_status:
            queryset = queryset.filter(status=requested_status)
        return Response(
            BookingSerializer(queryset, many=True).data
        )


class AgencyBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        profile = require_agency(request.user)
        booking = get_object_or_404(
            _booking_queryset(),
            pk=booking_id,
            agency=profile,
        )
        data = BookingSerializer(booking).data
        data["customer"] = {
            "id": str(booking.customer_id),
            "fullName": booking.customer.full_name,
            "phone": booking.customer.phone,
            "email": booking.customer.email,
        }
        return Response(data)


class AgencyBookingApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        serializer = BookingAgencyActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = agency_transition(
            user=request.user,
            booking_id=booking_id,
            action="approve",
            note=serializer.validated_data.get("note", ""),
        )
        booking = _booking_queryset().get(pk=booking.id)
        return Response(BookingSerializer(booking).data)


class AgencyBookingRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        serializer = BookingRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = agency_transition(
            user=request.user,
            booking_id=booking_id,
            action="reject",
            note=serializer.validated_data["reason"],
        )
        booking = _booking_queryset().get(pk=booking.id)
        return Response(BookingSerializer(booking).data)


class AgencyBookingPickupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = agency_transition(
            user=request.user,
            booking_id=booking_id,
            action="pickup",
        )
        booking = _booking_queryset().get(pk=booking.id)
        return Response(BookingSerializer(booking).data)


class AgencyBookingReturnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = agency_transition(
            user=request.user,
            booking_id=booking_id,
            action="return",
        )
        booking = _booking_queryset().get(pk=booking.id)
        return Response(BookingSerializer(booking).data)
