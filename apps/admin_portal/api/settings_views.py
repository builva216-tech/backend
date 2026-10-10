from decimal import Decimal

from django.db import transaction
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAdminStaff
from apps.accounts.api.authentication import AccountSessionAuthentication
from apps.accounts.models import AccountAuditEvent
from apps.agencies.models import SubscriptionPlan
from apps.core.api.exceptions import Conflict
from apps.core.models import BugReport, StoredUpload
from apps.core.api.protected_files import BinaryFileView, protected_file_response


class AdminStoredUploadView(BinaryFileView):
    permission_classes = [IsAdminStaff]
    authentication_classes = [AccountSessionAuthentication, SessionAuthentication]

    def get(self, request, upload_name):
        upload = get_object_or_404(StoredUpload, pk=upload_name)
        return protected_file_response(ContentFile(bytes(upload.content), name=upload.name))


class PlanSerializer(serializers.ModelSerializer):
    monthlyTnd = serializers.DecimalField(source='monthly_tnd', max_digits=9, decimal_places=2, min_value=Decimal('0'), coerce_to_string=False)
    priceText = serializers.CharField(source='price_text', max_length=120, allow_blank=True)
    isActive = serializers.BooleanField(source='is_active')
    cars = serializers.IntegerField(min_value=1, max_value=100000)
    branches = serializers.IntegerField(min_value=1, max_value=10000)
    revision = serializers.IntegerField(min_value=0)

    class Meta:
        model = SubscriptionPlan
        fields = ('code', 'name', 'monthlyTnd', 'priceText', 'description', 'cars', 'branches', 'isActive', 'recommended', 'revision')
        read_only_fields = ('code',)

    def validate(self, attrs):
        if 'revision' not in attrs:
            raise serializers.ValidationError({'revision': 'Reload the plan before saving.'})
        return attrs


class AdminPlanListView(APIView):
    permission_classes = [IsAdminStaff]

    def get(self, request):
        return Response(PlanSerializer(SubscriptionPlan.objects.all(), many=True).data)


class AdminPlanDetailView(APIView):
    permission_classes = [IsAdminStaff]

    @transaction.atomic
    def patch(self, request, code):
        row = get_object_or_404(SubscriptionPlan.objects.select_for_update(), code=code)
        serializer = PlanSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data['revision'] != row.revision:
            raise Conflict('Another administrator changed this plan. Reload before saving.')
        serializer.save(revision=row.revision + 1)
        AccountAuditEvent.objects.create(actor=request.user, action='subscription_plan_updated', reason=f'Updated {row.code} plan')
        return Response(PlanSerializer(row).data)


class AdminBugReportSerializer(serializers.ModelSerializer):
    reporterEmail = serializers.EmailField(source='reporter_email', read_only=True)
    reporterName = serializers.CharField(source='reporter_name', read_only=True)
    emailStatus = serializers.CharField(source='email_status', read_only=True)
    appVersion = serializers.CharField(source='app_version', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = BugReport
        fields = ('id', 'title', 'description', 'steps', 'reporterEmail', 'reporterName', 'platform', 'appVersion', 'emailStatus', 'status', 'createdAt')
        read_only_fields = ('id', 'title', 'description', 'steps', 'platform')


class AdminBugReportListView(APIView):
    permission_classes = [IsAdminStaff]

    def get(self, request):
        rows = BugReport.objects.all()
        if request.query_params.get('status') in ('open', 'resolved'):
            rows = rows.filter(status=request.query_params['status'])
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (TypeError, ValueError):
            raise serializers.ValidationError({'page': 'Use a positive integer.'})
        return Response({'count': rows.count(), 'results': AdminBugReportSerializer(rows[(page-1)*25:page*25], many=True).data})


class AdminBugReportDetailView(APIView):
    permission_classes = [IsAdminStaff]

    @transaction.atomic
    def patch(self, request, report_id):
        row = get_object_or_404(BugReport.objects.select_for_update(), pk=report_id)
        if request.data.get('retryEmail') is True:
            if row.email_status == 'sent':
                raise Conflict('This report email was already sent.')
            row.email_status = 'queued'
            row.email_attempts = 0
            row.next_delivery_at = timezone.now()
            row.save(update_fields=['email_status', 'email_attempts', 'next_delivery_at'])
        serializer = AdminBugReportSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
