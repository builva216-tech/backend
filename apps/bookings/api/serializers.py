from rest_framework import serializers

from apps.fleet.api.serializers import (
    CarReadSerializer,
    ExtraOptionSerializer,
    InsuranceOptionSerializer,
)
from apps.fleet.models import Car, ExtraOption, InsuranceOption

from ..models import (
    Booking,
    BookingExtra,
    BookingInsurance,
)


class BookingExtraSerializer(serializers.ModelSerializer):
    pricingType = serializers.CharField(source="pricing_type")
    unitPrice = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()

    class Meta:
        model = BookingExtra
        fields = (
            "id",
            "name",
            "pricingType",
            "unitPrice",
            "quantity",
            "totalPrice",
        )

    def get_unitPrice(self, obj):
        return float(obj.unit_price)

    def get_totalPrice(self, obj):
        return float(obj.total_price)


class BookingInsuranceSerializer(serializers.ModelSerializer):
    dailyPrice = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()
    securityDeposit = serializers.SerializerMethodField()

    class Meta:
        model = BookingInsurance
        fields = (
            "id",
            "name",
            "dailyPrice",
            "totalPrice",
            "securityDeposit",
        )

    def get_dailyPrice(self, obj):
        return float(obj.daily_price)

    def get_totalPrice(self, obj):
        return float(obj.total_price)

    def get_securityDeposit(self, obj):
        return float(obj.security_deposit)


class BookingSerializer(serializers.ModelSerializer):
    carId = serializers.UUIDField(source="car_id")
    agencyId = serializers.UUIDField(source="agency.user_id")
    customerId = serializers.UUIDField(source="customer_id")
    pickupDate = serializers.DateTimeField(source="pickup_at")
    returnDate = serializers.DateTimeField(source="return_at")
    totalDays = serializers.IntegerField(source="rental_days")
    dailyPrice = serializers.SerializerMethodField()
    basePrice = serializers.SerializerMethodField()
    extrasTotal = serializers.SerializerMethodField()
    insuranceTotal = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()
    securityDeposit = serializers.SerializerMethodField()
    pickupGovernorateCode = serializers.CharField(
        source="pickup_governorate_id"
    )
    pickupCity = serializers.CharField(source="pickup_city")
    paymentMethod = serializers.CharField(
        source="payment_method",
        read_only=True,
    )
    customerNote = serializers.CharField(source="customer_note")
    agencyNote = serializers.CharField(source="agency_note")
    agencyRespondedAt = serializers.DateTimeField(
        source="agency_responded_at",
        allow_null=True,
    )
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    extras = BookingExtraSerializer(many=True)
    insurance = BookingInsuranceSerializer(allow_null=True)
    payment = serializers.SerializerMethodField()
    car = CarReadSerializer(read_only=True)
    agency = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "carId",
            "agencyId",
            "customerId",
            "pickupDate",
            "returnDate",
            "totalDays",
            "dailyPrice",
            "basePrice",
            "extrasTotal",
            "insuranceTotal",
            "totalPrice",
            "securityDeposit",
            "pickupGovernorateCode",
            "pickupCity",
            "paymentMethod",
            "status",
            "customerNote",
            "agencyNote",
            "agencyRespondedAt",
            "createdAt",
            "updatedAt",
            "extras",
            "insurance",
            "payment",
            "car",
            "agency",
            "customer",
        )

    def get_dailyPrice(self, obj):
        return float(obj.daily_price_snapshot)

    def get_basePrice(self, obj):
        return float(obj.base_price)

    def get_extrasTotal(self, obj):
        return float(obj.extras_total)

    def get_insuranceTotal(self, obj):
        return float(obj.insurance_total)

    def get_totalPrice(self, obj):
        return float(obj.total_price)

    def get_securityDeposit(self, obj):
        return float(obj.security_deposit)

    def get_payment(self, obj):
        payment = getattr(obj, "payment", None)
        if payment is None:
            return None
        return {
            "id": str(payment.id),
            "method": payment.method,
            "status": payment.status,
            "rentalAmount": float(payment.rental_amount),
            "depositAmount": float(payment.deposit_amount),
            "paidAt": (
                payment.paid_at.isoformat()
                if payment.paid_at
                else None
            ),
        }


    def get_agency(self, obj):
        profile = obj.agency
        return {
            "agencyId": str(profile.user_id),
            "agencyName": profile.agency_name,
            "phone": profile.user.phone,
            "email": profile.user.email,
            "governorateCode": profile.governorate_id,
            "city": profile.city,
        }

    def get_customer(self, obj):
        user = obj.customer
        return {
            "customerId": str(user.id),
            "fullName": user.full_name,
            "phone": user.phone,
            "email": user.email,
        }


class BookingCreateSerializer(serializers.Serializer):
    carId = serializers.UUIDField()
    pickupDate = serializers.DateTimeField()
    returnDate = serializers.DateTimeField()
    extraIds = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    insuranceId = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    customerNote = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        default="",
    )


class BookingQuoteSerializer(BookingCreateSerializer):
    pass


class BookingAgencyActionSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        default="",
    )


class BookingRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(
        min_length=3,
        max_length=1000,
    )
