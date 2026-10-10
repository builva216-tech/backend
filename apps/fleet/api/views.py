from apps.core.api.protected_files import BinaryFileView, protected_file_response
from apps.agencies.subscriptions import require_capacity, require_management
import json

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAgency
from apps.agencies.models import AgencyVerificationStatus
from apps.accounts.models import AccountStatus

from ..models import (
    AvailabilityBlock,
    Car,
    CarPhoto,
    CarStatus,
    ExtraOption,
    InsuranceOption,
)
from ..services import (
    can_publish_car,
    create_availability_block,
    require_approved_agency,
)
from .serializers import (
    AgencyCarReadSerializer,
    AvailabilityBlockSerializer,
    AvailabilityBlockWriteSerializer,
    CarReadSerializer,
    CarWriteSerializer,
    ExtraOptionSerializer,
    ExtraOptionWriteSerializer,
    InsuranceOptionSerializer,
    InsuranceOptionWriteSerializer,
)


def _public_car_queryset():
    return (
        Car.objects.select_related(
            "agency",
            "agency__user",
            "governorate",
        )
        .prefetch_related("photos")
        .filter(
            status=CarStatus.PUBLISHED,
            is_available=True,
            agency__verification_status=(
                AgencyVerificationStatus.APPROVED
            ),
            agency__user__account_status=AccountStatus.ACTIVE,
            agency__user__is_active=True,
        )
    )


class PublicCarListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        queryset = _public_car_queryset()

        governorate_code = request.query_params.get(
            "governorateCode",
            "",
        ).strip().upper()
        category = request.query_params.get("category", "").strip()
        search = request.query_params.get("search", "").strip()

        if governorate_code:
            queryset = queryset.filter(
                governorate_id=governorate_code
            )

        if category:
            queryset = queryset.filter(category=category)

        if search:
            queryset = queryset.filter(
                Q(brand__icontains=search)
                | Q(model__icontains=search)
                | Q(city__icontains=search)
            )

        starts_at = parse_datetime(
            request.query_params.get("startsAt", "")
        )
        ends_at = parse_datetime(
            request.query_params.get("endsAt", "")
        )

        if starts_at and ends_at and ends_at > starts_at:
            queryset = queryset.exclude(
                availability_blocks__starts_at__lt=ends_at,
                availability_blocks__ends_at__gt=starts_at,
            )

            try:
                from apps.bookings.models import BookingStatus
                blocked_statuses = (
                    BookingStatus.APPROVED,
                    BookingStatus.CONFIRMED,
                    BookingStatus.ACTIVE,
                )
                queryset = queryset.exclude(
                    bookings__status__in=blocked_statuses,
                    bookings__pickup_at__lt=ends_at,
                    bookings__return_at__gt=starts_at,
                )
            except Exception:
                pass

        data = CarReadSerializer(
            queryset.distinct(),
            many=True,
        ).data
        return Response(data)


class PublicCarDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, car_id):
        car = get_object_or_404(
            _public_car_queryset(),
            pk=car_id,
        )
        return Response(CarReadSerializer(car).data)


class PublicCarPhotoView(BinaryFileView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, car_id, photo_id):
        photo = get_object_or_404(
            CarPhoto.objects.select_related(
                "car__agency__user",
                "car__agency",
            ),
            pk=photo_id,
            car_id=car_id,
            car__status=CarStatus.PUBLISHED,
            car__agency__verification_status=(
                AgencyVerificationStatus.APPROVED
            ),
            car__agency__user__account_status=AccountStatus.ACTIVE,
        )

        response = protected_file_response(photo.image)
        response["Cache-Control"] = "public, max-age=3600"
        return response


class PublicCarConditionVideoView(BinaryFileView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, car_id):
        car = get_object_or_404(
            _public_car_queryset(),
            pk=car_id,
        )

        if not car.condition_video:
            return Response(
                {"detail": "Condition video was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = protected_file_response(car.condition_video)
        response["Cache-Control"] = "public, max-age=3600"
        return response


class AgencyCarListCreateView(APIView):
    permission_classes = [IsAgency]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        profile = require_approved_agency(request.user)
        queryset = (
            Car.objects.filter(agency=profile)
            .exclude(status=CarStatus.ARCHIVED)
            .select_related("agency", "governorate")
            .prefetch_related("photos")
        )
        return Response(
            AgencyCarReadSerializer(queryset, many=True).data
        )

    @transaction.atomic
    def post(self, request):
        require_management(request.user.agency_profile)
        profile = require_approved_agency(request.user)
        require_capacity(profile, 'cars')
        serializer = CarWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        car = Car.objects.create(
            agency=profile,
            brand=data["brand"].strip(),
            model=data["model"].strip(),
            year=data["year"],
            category=data["category"],
            transmission=data["transmission"],
            fuel_type=data["fuelType"],
            seats=data["seats"],
            doors=data["doors"],
            color=data.get("color", "").strip(),
            mileage_km=data.get("mileageKm"),
            plate_number=data.get("plateNumber", "").strip(),
            daily_price=data["dailyPrice"],
            governorate=data["governorateCode"],
            city=data.get("city", "").strip(),
            status=data.get("status", CarStatus.PUBLISHED),
            is_available=data.get("isAvailable", True),
            registration_expiry=data.get("registrationExpiry"),
            insurance_expiry=data.get("insuranceExpiry"),
            condition_video=request.FILES.get("conditionVideo"),
        )

        photos = request.FILES.getlist("photos")[:8]
        for index, image in enumerate(photos):
            CarPhoto.objects.create(
                car=car,
                image=image,
                position=index,
            )

        if car.status == CarStatus.PUBLISHED and not can_publish_car(car):
            car.status = CarStatus.DRAFT
            car.save(update_fields=["status", "updated_at"])

        car.refresh_from_db()
        return Response(
            AgencyCarReadSerializer(car).data,
            status=status.HTTP_201_CREATED,
        )


class AgencyCarDetailView(APIView):
    permission_classes = [IsAgency]
    parser_classes = [MultiPartParser, FormParser]

    def _get_car(self, request, car_id):
        profile = require_approved_agency(request.user)
        return get_object_or_404(
            Car.objects.select_related(
                "agency",
                "governorate",
            ).prefetch_related("photos"),
            pk=car_id,
            agency=profile,
        )

    def get(self, request, car_id):
        return Response(
            AgencyCarReadSerializer(
                self._get_car(request, car_id)
            ).data
        )

    @transaction.atomic
    def patch(self, request, car_id):
        require_management(request.user.agency_profile)
        car = self._get_car(request, car_id)
        serializer = CarWriteSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if car.status == CarStatus.ARCHIVED and data.get('status', car.status) != CarStatus.ARCHIVED:
            require_capacity(car.agency, 'cars')

        mapping = {
            "brand": "brand",
            "model": "model",
            "year": "year",
            "category": "category",
            "transmission": "transmission",
            "fuelType": "fuel_type",
            "seats": "seats",
            "doors": "doors",
            "color": "color",
            "mileageKm": "mileage_km",
            "plateNumber": "plate_number",
            "dailyPrice": "daily_price",
            "governorateCode": "governorate",
            "city": "city",
            "status": "status",
            "isAvailable": "is_available",
            "registrationExpiry": "registration_expiry",
            "insuranceExpiry": "insurance_expiry",
        }

        for source, target in mapping.items():
            if source in data:
                setattr(car, target, data[source])

        if "conditionVideo" in request.FILES:
            car.condition_video = request.FILES["conditionVideo"]

        car.save()

        if "existingPhotoIds" in data:
            keep_ids = data["existingPhotoIds"]
            car.photos.exclude(id__in=keep_ids).delete()

        starting_position = car.photos.count()
        for offset, image in enumerate(
            request.FILES.getlist("photos")[:8]
        ):
            CarPhoto.objects.create(
                car=car,
                image=image,
                position=starting_position + offset,
            )

        if car.status == CarStatus.PUBLISHED and not can_publish_car(car):
            car.status = CarStatus.DRAFT
            car.save(update_fields=["status", "updated_at"])

        return Response(AgencyCarReadSerializer(car).data)

    @transaction.atomic
    def delete(self, request, car_id):
        require_management(request.user.agency_profile)
        car = self._get_car(request, car_id)
        car.status = CarStatus.ARCHIVED
        car.is_available = False
        car.save(
            update_fields=[
                "status",
                "is_available",
                "updated_at",
            ]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AgencyAvailabilityBlockListCreateView(APIView):
    permission_classes = [IsAgency]

    def _get_car(self, request, car_id):
        profile = require_approved_agency(request.user)
        return get_object_or_404(
            Car,
            pk=car_id,
            agency=profile,
        )

    def get(self, request, car_id):
        car = self._get_car(request, car_id)
        return Response(
            AvailabilityBlockSerializer(
                car.availability_blocks.all(),
                many=True,
            ).data
        )

    def post(self, request, car_id):
        require_management(request.user.agency_profile)
        car = self._get_car(request, car_id)
        serializer = AvailabilityBlockWriteSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        block = create_availability_block(
            user=request.user,
            car=car,
            starts_at=data["startsAt"],
            ends_at=data["endsAt"],
            reason=data.get("reason", ""),
        )

        return Response(
            AvailabilityBlockSerializer(block).data,
            status=status.HTTP_201_CREATED,
        )


class AgencyAvailabilityBlockDetailView(APIView):
    permission_classes = [IsAgency]

    def delete(self, request, car_id, block_id):
        require_management(request.user.agency_profile)
        profile = require_approved_agency(request.user)
        block = get_object_or_404(
            AvailabilityBlock,
            pk=block_id,
            car_id=car_id,
            car__agency=profile,
        )
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AgencyExtraOptionListCreateView(APIView):
    permission_classes = [IsAgency]

    def get(self, request):
        profile = require_approved_agency(request.user)
        return Response(
            ExtraOptionSerializer(
                profile.extra_options.all(),
                many=True,
            ).data
        )

    def post(self, request):
        require_management(request.user.agency_profile)
        profile = require_approved_agency(request.user)
        serializer = ExtraOptionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        option = ExtraOption.objects.create(
            agency=profile,
            name=data["name"].strip(),
            description=data.get("description", "").strip(),
            pricing_type=data["pricingType"],
            price=data["price"],
            estimated_cost=data.get("estimatedCost", 0),
            is_active=data.get("isActive", True),
        )
        return Response(
            ExtraOptionSerializer(option).data,
            status=status.HTTP_201_CREATED,
        )


class AgencyInsuranceOptionListCreateView(APIView):
    permission_classes = [IsAgency]

    def get(self, request):
        profile = require_approved_agency(request.user)
        return Response(
            InsuranceOptionSerializer(
                profile.insurance_options.all(),
                many=True,
            ).data
        )

    def post(self, request):
        require_management(request.user.agency_profile)
        profile = require_approved_agency(request.user)
        serializer = InsuranceOptionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        option = InsuranceOption.objects.create(
            agency=profile,
            name=data["name"].strip(),
            description=data.get("description", "").strip(),
            daily_price=data["dailyPrice"],
            estimated_daily_cost=data.get("estimatedDailyCost", 0),
            security_deposit=data.get("securityDeposit", 0),
            is_active=data.get("isActive", True),
        )
        return Response(
            InsuranceOptionSerializer(option).data,
            status=status.HTTP_201_CREATED,
        )


class PublicAgencyOptionsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, agency_id):
        extras = ExtraOption.objects.filter(
            agency__user_id=agency_id,
            agency__verification_status=(
                AgencyVerificationStatus.APPROVED
            ),
            is_active=True,
        )
        insurance = InsuranceOption.objects.filter(
            agency__user_id=agency_id,
            agency__verification_status=(
                AgencyVerificationStatus.APPROVED
            ),
            is_active=True,
        )
        return Response(
            {
                "extras": ExtraOptionSerializer(
                    extras,
                    many=True,
                ).data,
                "insurance": InsuranceOptionSerializer(
                    insurance,
                    many=True,
                ).data,
            }
        )


class AgencyExtraOptionDetailView(APIView):
    permission_classes = [IsAgency]

    def _get_option(self, request, option_id):
        profile = require_approved_agency(request.user)
        return get_object_or_404(
            ExtraOption,
            pk=option_id,
            agency=profile,
        )

    def patch(self, request, option_id):
        require_management(request.user.agency_profile)
        option = self._get_option(request, option_id)
        serializer = ExtraOptionWriteSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mapping = {
            "name": "name",
            "description": "description",
            "pricingType": "pricing_type",
            "price": "price",
            "estimatedCost": "estimated_cost",
            "isActive": "is_active",
        }

        for source, target in mapping.items():
            if source in data:
                setattr(option, target, data[source])

        option.save()
        return Response(ExtraOptionSerializer(option).data)

    def delete(self, request, option_id):
        require_management(request.user.agency_profile)
        option = self._get_option(request, option_id)
        option.is_active = False
        option.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AgencyInsuranceOptionDetailView(APIView):
    permission_classes = [IsAgency]

    def _get_option(self, request, option_id):
        profile = require_approved_agency(request.user)
        return get_object_or_404(
            InsuranceOption,
            pk=option_id,
            agency=profile,
        )

    def patch(self, request, option_id):
        require_management(request.user.agency_profile)
        option = self._get_option(request, option_id)
        serializer = InsuranceOptionWriteSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mapping = {
            "name": "name",
            "description": "description",
            "dailyPrice": "daily_price",
            "estimatedDailyCost": "estimated_daily_cost",
            "securityDeposit": "security_deposit",
            "isActive": "is_active",
        }

        for source, target in mapping.items():
            if source in data:
                setattr(option, target, data[source])

        option.save()
        return Response(InsuranceOptionSerializer(option).data)

    def delete(self, request, option_id):
        require_management(request.user.agency_profile)
        option = self._get_option(request, option_id)
        option.is_active = False
        option.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
