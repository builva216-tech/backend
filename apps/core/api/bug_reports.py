"""Authenticated reports saved durably, then emailed to the support mailbox."""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.core.models import BugReport


class BugReportSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=5, max_length=120)
    description = serializers.CharField(min_length=10, max_length=5000)
    steps = serializers.CharField(max_length=3000, required=False, allow_blank=True)
    appVersion = serializers.CharField(max_length=60, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=60, required=False, allow_blank=True)

    def validate_title(self, value):
        if "\r" in value or "\n" in value:
            raise serializers.ValidationError("Use a single-line title.")
        return value


class BugReportUserThrottle(UserRateThrottle):
    scope = "bug_report_user"


class BugReportIPThrottle(SimpleRateThrottle):
    scope = "bug_report_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class BugReportView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [BugReportUserThrottle, BugReportIPThrottle]

    def post(self, request):
        serializer = BugReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        report = BugReport.objects.create(
            reporter=user, reporter_email=user.email, reporter_name=user.full_name,
            reporter_role=user.role, title=data['title'], description=data['description'],
            steps=data.get('steps', ''), app_version=data.get('appVersion', ''),
            platform=data.get('platform', ''),
        )
        return Response({'id': str(report.pk), 'emailStatus': report.email_status,
                         'detail': 'Your report has been saved. Thank you.'},
                        status=status.HTTP_201_CREATED)
