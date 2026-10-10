from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.bookings.api.serializers import BookingSerializer
from apps.bookings.models import Booking, BookingStatus

from ..models import (
    AgencyCustomerRating,
    CustomerRentalReview,
)
from ..services import (
    submit_agency_customer_rating,
    submit_customer_review,
)
from .serializers import (
    AgencyCustomerRatingSerializer,
    AgencyCustomerRatingWriteSerializer,
    CustomerRentalReviewSerializer,
    CustomerReviewWriteSerializer,
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


class ReviewBookingContextView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        booking = get_object_or_404(
            _booking_queryset(),
            pk=booking_id,
        )

        is_customer = (
            request.user.role == UserRole.CUSTOMER
            and booking.customer_id == request.user.id
        )
        is_agency = (
            request.user.role == UserRole.AGENCY
            and booking.agency.user_id == request.user.id
        )

        if not (is_customer or is_agency):
            return Response(
                {"detail": "Booking access denied."},
                status=403,
            )

        return Response(
            BookingSerializer(booking).data
        )


class CustomerReviewByBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.only(
                "id",
                "customer_id",
            ),
            pk=booking_id,
        )

        if request.user.id != booking.customer_id:
            return Response(
                {
                    "detail": (
                        "This booking does not belong to your account."
                    )
                },
                status=403,
            )

        review = (
            CustomerRentalReview.objects.filter(
                booking_id=booking_id
            )
            .select_related("agency")
            .first()
        )

        return Response(
            {
                "review": (
                    None
                    if review is None
                    else CustomerRentalReviewSerializer(review).data
                )
            }
        )


class AgencyCustomerRatingByBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("agency__user"),
            pk=booking_id,
        )

        if request.user.id != booking.agency.user_id:
            return Response(
                {
                    "detail": (
                        "This booking does not belong to your agency."
                    )
                },
                status=403,
            )

        rating = (
            AgencyCustomerRating.objects.filter(
                booking_id=booking_id
            )
            .select_related("agency")
            .first()
        )

        return Response(
            {
                "rating": (
                    None
                    if rating is None
                    else AgencyCustomerRatingSerializer(rating).data
                )
            }
        )


class CustomerReviewSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        serializer = CustomerReviewWriteSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        review = submit_customer_review(
            user=request.user,
            booking_id=booking_id,
            car_rating=serializer.validated_data["carRating"],
            agency_rating=serializer.validated_data["agencyRating"],
            comment=serializer.validated_data.get("comment", ""),
        )

        return Response(
            CustomerRentalReviewSerializer(review).data,
            status=201,
        )


class AgencyCustomerRatingSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        serializer = AgencyCustomerRatingWriteSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        rating = submit_agency_customer_rating(
            user=request.user,
            booking_id=booking_id,
            punctuality_rating=serializer.validated_data[
                "punctualityRating"
            ],
            car_care_rating=serializer.validated_data[
                "carCareRating"
            ],
            communication_rating=serializer.validated_data[
                "communicationRating"
            ],
            private_comment=serializer.validated_data.get(
                "privateComment",
                "",
            ),
        )

        return Response(
            AgencyCustomerRatingSerializer(rating).data,
            status=201,
        )


class AgencyReputationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, agency_id):
        queryset = (
            CustomerRentalReview.objects.filter(
                agency__user_id=agency_id
            )
            .select_related("agency")
        )

        aggregate = queryset.aggregate(
            average=Avg("agency_rating"),
            count=Count("id"),
        )

        return Response(
            {
                "agencyId": str(agency_id),
                "averageRating": float(
                    aggregate["average"] or 0
                ),
                "reviewCount": aggregate["count"],
                "reviews": CustomerRentalReviewSerializer(
                    queryset[:50],
                    many=True,
                ).data,
            }
        )


class CarReputationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, car_id):
        queryset = (
            CustomerRentalReview.objects.filter(
                car_id=car_id
            )
            .select_related("agency")
        )

        aggregate = queryset.aggregate(
            average=Avg("car_rating"),
            count=Count("id"),
        )

        return Response(
            {
                "carId": str(car_id),
                "averageRating": float(
                    aggregate["average"] or 0
                ),
                "reviewCount": aggregate["count"],
                "reviews": CustomerRentalReviewSerializer(
                    queryset[:50],
                    many=True,
                ).data,
            }
        )


class CustomerTrustView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        ratings_queryset = (
            AgencyCustomerRating.objects.filter(
                customer_id=customer_id
            )
            .select_related("agency")
        )

        ratings = list(ratings_queryset[:50])

        average = 0.0
        if ratings:
            average = sum(
                rating.trust_score
                for rating in ratings
            ) / len(ratings)

        completed_rentals_count = (
            Booking.objects.filter(
                customer_id=customer_id,
                status=BookingStatus.COMPLETED,
            ).count()
        )

        return Response(
            {
                "customerId": str(customer_id),
                "averageRating": average,
                "ratingCount": len(ratings),
                "completedRentalsCount": completed_rentals_count,
                "ratings": AgencyCustomerRatingSerializer(
                    ratings,
                    many=True,
                ).data,
            }
        )
