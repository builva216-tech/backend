from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from .models import Notification, PushDevice, AppRelease
from .services import register_device, token_hash


class DeviceThrottle(UserRateThrottle):
    scope = 'push_device'


class DeviceInput(serializers.Serializer):
    token = serializers.RegexField(r'^[A-Za-z0-9_:\-\.]+$', min_length=20, max_length=4096, write_only=True)
    app = serializers.ChoiceField(choices=['main', 'admin'])
    platform = serializers.ChoiceField(choices=['android', 'ios'])

    def validate_app(self, value):
        if value == 'admin' and not self.context['request'].user.is_staff:
            raise serializers.ValidationError('Staff access is required.')
        return value


class DeviceView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [DeviceThrottle]

    def post(self, request):
        s = DeviceInput(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        register_device(user=request.user, **s.validated_data)
        return Response({'registered': True}, status=201)

    def delete(self, request):
        token = request.data.get('token')
        if isinstance(token, str) and len(token) <= 4096:
            PushDevice.objects.filter(user=request.user, token_hash=token_hash(token)).update(active=False)
        return Response(status=204)


class InboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Keyset pagination keeps older booking links accessible without leaking accounts.
        qs = Notification.objects.filter(user=request.user)
        cursor = request.query_params.get('before')
        if cursor:
            anchor = get_object_or_404(qs, pk=serializers.UUIDField().run_validation(cursor))
            from django.db.models import Q
            qs = qs.filter(Q(created_at__lt=anchor.created_at) | Q(created_at=anchor.created_at, id__lt=anchor.id))
        items = list(qs[:51])
        page = items[:50]
        return Response({'items': [{'id': str(n.id), 'kind': n.kind, 'title': n.title,
            'body': n.body, 'bookingId': str(n.booking_id) if n.booking_id else None,
            'createdAt': n.created_at, 'readAt': n.read_at} for n in page],
            'unread': Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
            'next': str(page[-1].id) if len(items) > 50 else None})


class ReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        item = get_object_or_404(Notification, user=request.user, pk=notification_id)
        if item.read_at is None:
            item.read_at = timezone.now()
            item.save(update_fields=['read_at'])
        return Response({'read': True})


class ReleaseView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        app, platform = request.query_params.get('app', 'main'), request.query_params.get('platform', 'android')
        if app not in ('main', 'admin') or platform not in ('android', 'ios'):
            return Response({'detail': 'Invalid app or platform.'}, status=400)
        release = AppRelease.objects.filter(app=app, platform=platform, published=True).order_by('-version_code').first()
        if release is None:
            return Response({'release': None})
        return Response({'release': {'versionCode': release.version_code, 'versionName': release.version_name,
            'url': release.update_url, 'notes': release.notes}})


urlpatterns = [path('notifications/', InboxView.as_view()),
    path('notifications/<uuid:notification_id>/read/', ReadView.as_view()),
    path('devices/', DeviceView.as_view()), path('app-release/', ReleaseView.as_view())]
