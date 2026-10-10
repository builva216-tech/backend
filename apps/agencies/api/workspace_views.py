from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from apps.accounts.api.permissions import IsAgency
from apps.agencies.models import AgencyBranch, AgencyProfile
from apps.agencies.subscriptions import public_entitlement, require_management, require_capacity
from apps.locations.models import Governorate
from apps.fleet.models import Car
from apps.fleet.services import require_approved_agency


class BranchSerializer(serializers.ModelSerializer):
    governorateCode = serializers.SlugRelatedField(source='governorate', slug_field='code', queryset=Governorate.objects.filter(is_active=True))
    isActive = serializers.BooleanField(source='is_active', required=False)
    carCount = serializers.SerializerMethodField()

    class Meta:
        model = AgencyBranch
        fields = ('id', 'name', 'address', 'governorateCode', 'city', 'latitude', 'longitude', 'isActive', 'carCount')
        read_only_fields = ('id', 'carCount')

    def get_carCount(self, obj):
        return obj.cars.exclude(status='archived').count()

    def validate(self, attrs):
        lat = attrs.get('latitude', self.instance.latitude if self.instance else None)
        lon = attrs.get('longitude', self.instance.longitude if self.instance else None)
        if (lat is None) != (lon is None):
            raise serializers.ValidationError('Latitude and longitude must be supplied together.')
        if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise serializers.ValidationError('Invalid coordinates.')
        name = attrs.get('name', self.instance.name if self.instance else '').strip()
        agency = self.context['agency']
        query = AgencyBranch.objects.filter(agency=agency, name=name)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError({'name': 'Branch name already exists.'})
        attrs['name'] = name
        return attrs


class SubscriptionView(APIView):
    permission_classes = [IsAgency]

    def get(self, request):
        return Response(public_entitlement(request.user.agency_profile))


class BranchListView(APIView):
    permission_classes = [IsAgency]

    def get(self, request):
        return Response(BranchSerializer(request.user.agency_profile.branches.all(), many=True).data)

    @transaction.atomic
    def post(self, request):
        agency = require_approved_agency(request.user)
        require_capacity(agency, 'branches')
        serializer = BranchSerializer(data=request.data, context={'agency': agency})
        serializer.is_valid(raise_exception=True)
        serializer.save(agency=agency)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BranchDetailView(APIView):
    permission_classes = [IsAgency]

    @transaction.atomic
    def patch(self, request, branch_id):
        agency = require_approved_agency(request.user)
        branch = get_object_or_404(AgencyBranch.objects.select_for_update(), pk=branch_id, agency=agency)
        require_management(agency)
        serializer = BranchSerializer(branch, data=request.data, partial=True, context={'agency': agency})
        serializer.is_valid(raise_exception=True)
        if not branch.is_active and serializer.validated_data.get('is_active') is True:
            require_capacity(agency, 'branches')
        serializer.save()
        return Response(serializer.data)


class BranchCarView(APIView):
    permission_classes = [IsAgency]

    @transaction.atomic
    def patch(self, request, branch_id, car_id):
        agency = require_approved_agency(request.user)
        require_management(agency)
        branch = get_object_or_404(AgencyBranch, pk=branch_id, agency=agency, is_active=True)
        car = get_object_or_404(Car.objects.select_for_update(), pk=car_id, agency=agency)
        car.branch = branch
        car.save(update_fields=['branch', 'updated_at'])
        return Response({'carId': str(car.id), 'branchId': str(branch.id)})


class PublicBranchesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, agency_id):
        agency = get_object_or_404(AgencyProfile, user_id=agency_id, verification_status='approved', user__is_active=True, user__account_status='active')
        return Response(BranchSerializer(agency.branches.filter(is_active=True), many=True).data)


class SubscriptionRequestThrottle(UserRateThrottle):
    scope = 'subscription_request'


class SubscriptionRequestView(APIView):
    permission_classes = [IsAgency]
    throttle_classes = [SubscriptionRequestThrottle]

    @transaction.atomic
    def post(self, request):
        from apps.agencies.models import AgencySubscriptionRequest
        from apps.agencies.models import SubscriptionPlan
        plan = request.data.get('plan')
        if not isinstance(plan, str) or not SubscriptionPlan.objects.filter(code=plan, is_active=True).exists():
            raise serializers.ValidationError({'plan': 'Select a valid plan.'})
        agency = AgencyProfile.objects.select_for_update().get(user=request.user)
        row, created = AgencySubscriptionRequest.objects.get_or_create(
            agency=agency, status='requested', defaults={'plan': plan})
        if not created and row.plan != plan:
            row.plan = plan
            row.save(update_fields=['plan'])
        return Response({'id': row.pk, 'plan': row.plan, 'status': row.status}, status=201 if created else 200)
