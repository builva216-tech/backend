import math
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAdminStaff
from apps.accounts.models import (
    AccountAuditEvent,
    PasswordRecoveryChallenge,
    User,
    UserRole,
)
from apps.agencies.models import AgencyProfile, AgencyVerificationSubmission
from apps.bookings.models import Booking
from apps.customer_verifications.models import CustomerVerificationSubmission
from apps.fleet.models import Car
from apps.payments.models import Payment


class WorkspacePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "pageSize"
    max_page_size = 100


def account_payload(user):
    agency = None
    if user.role == UserRole.AGENCY:
        try:
            agency = user.agency_profile
        except AgencyProfile.DoesNotExist:
            pass
    if hasattr(user, "latest_verification"):
        latest_status = user.latest_verification
    else:
        latest = (
            agency.verification_submissions.order_by("-attempt_number").first()
            if agency
            else None
        )
        latest_status = latest.status if latest else None
    return {
        "id": str(user.id),
        "fullName": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "accountStatus": user.account_status,
        "isActive": user.is_active,
        "isEmailVerified": user.is_email_verified,
        "joinedAt": user.date_joined.isoformat(),
        "agencyProfileId": str(agency.id) if agency else None,
        "agencyName": agency.agency_name if agency else None,
        "verificationStage": (latest_status or "notSubmitted") if agency else None,
    }


class AdminAccountListView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        latest = AgencyVerificationSubmission.objects.filter(
            agency_profile__user_id=OuterRef("pk")
        ).order_by("-attempt_number")
        users = (
            User.objects.select_related("agency_profile")
            .annotate(latest_verification=Subquery(latest.values("status")[:1]))
            .order_by("-date_joined", "id")
        )
        role = request.query_params.get("role", "").strip()
        if role:
            if role not in UserRole.values:
                raise ValidationError({"role": ["Select a valid role."]})
            users = users.filter(role=role)
        query = request.query_params.get("q", "").strip()[:120]
        if query:
            users = users.filter(
                Q(full_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
                | Q(agency_profile__agency_name__icontains=query)
            )
        active = request.query_params.get("active", "")
        if active not in ["", "true", "false"]:
            raise ValidationError({"active": ["Use true or false."]})
        if active:
            users = users.filter(is_active=active == "true")
        paginator = WorkspacePagination()
        page = paginator.paginate_queryset(users, request)
        return paginator.get_paginated_response(
            [account_payload(user) for user in page]
        )


class AccountAccessSerializer(serializers.Serializer):
    isActive = serializers.BooleanField()
    reason = serializers.CharField(min_length=5, max_length=500)


class AdminAccountAccessView(APIView):
    permission_classes = (IsAdminStaff,)

    def patch(self, request, user_id):
        serializer = AccountAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        active = serializer.validated_data["isActive"]
        with transaction.atomic():
            # Consistent order prevents two administrators concurrently removing
            # the last operational admin account.
            list(
                User.objects.select_for_update()
                .filter(role=UserRole.ADMIN, is_staff=True)
                .order_by("id")
            )
            user = get_object_or_404(User.objects.select_for_update(), id=user_id)
            if user.id == request.user.id and not active:
                raise ValidationError(
                    {"isActive": ["You cannot suspend your own account."]}
                )
            if (
                user.role == UserRole.ADMIN
                and user.is_staff
                and not active
                and user.is_active
            ):
                if (
                    User.objects.filter(
                        role=UserRole.ADMIN, is_staff=True, is_active=True
                    ).count()
                    <= 1
                ):
                    raise ValidationError(
                        {"isActive": ["At least one active administrator must remain."]}
                    )
            if user.is_active != active:
                user.is_active = active
                if not active:
                    user.session_version += 1
                user.save(update_fields=["is_active", "session_version", "updated_at"])
                AccountAuditEvent.objects.create(
                    actor=request.user,
                    subject=user,
                    action="account_reactivated" if active else "account_suspended",
                    reason=serializer.validated_data["reason"],
                )
        return Response(account_payload(user))


class AdminAuditListView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        events = AccountAuditEvent.objects.select_related("actor", "subject").order_by(
            "-created_at", "id"
        )
        paginator = WorkspacePagination()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(
            [
                {
                    "id": str(event.id),
                    "action": event.action,
                    "actorName": event.actor.full_name
                    if event.actor
                    else "Self-service / unavailable",
                    "subjectName": event.subject.full_name
                    if event.subject
                    else "Unavailable",
                    "reason": event.reason,
                    "createdAt": event.created_at.isoformat(),
                }
                for event in page
            ]
        )


def _amount(queryset, field):
    return queryset.aggregate(value=Sum(field))["value"] or Decimal("0")


class AdminBusinessAnalyticsView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"days": ["Use 7, 30 or 90."]}) from exc
        if days not in [7, 30, 90]:
            raise ValidationError({"days": ["Use 7, 30 or 90."]})
        zone = ZoneInfo(settings.TIME_ZONE)
        today = timezone.localdate()
        start_day = today - timedelta(days=days - 1)
        end_day = today + timedelta(days=1)
        start = datetime.combine(start_day, time.min, tzinfo=zone)
        end = datetime.combine(end_day, time.min, tzinfo=zone)
        requests = Booking.objects.filter(created_at__gte=start, created_at__lt=end)
        collections = Payment.objects.filter(
            status="paid", paid_at__gte=start, paid_at__lt=end
        )
        prior_start = datetime.combine(
            start_day - timedelta(days=days), time.min, tzinfo=zone
        )
        prior_requests = Booking.objects.filter(
            created_at__gte=prior_start, created_at__lt=start
        )
        prior_collections = Payment.objects.filter(
            status="paid", paid_at__gte=prior_start, paid_at__lt=start
        )
        daily_requests = {
            row["day"]: row["count"]
            for row in requests.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        }
        daily_collections = {
            row["day"]: row["total"]
            for row in collections.annotate(day=TruncDate("paid_at"))
            .values("day")
            .annotate(total=Sum("rental_amount"))
        }
        width = math.ceil(days / 10)
        buckets = []
        cursor = start_day
        while cursor < end_day:
            until = min(cursor + timedelta(days=width), end_day)
            bucket_days = [
                cursor + timedelta(days=i) for i in range((until - cursor).days)
            ]
            buckets.append(
                {
                    "start": cursor.isoformat(),
                    "endExclusive": until.isoformat(),
                    "requests": sum(daily_requests.get(day, 0) for day in bucket_days),
                    "rentalCollections": str(
                        sum(
                            (
                                daily_collections.get(day, Decimal("0"))
                                for day in bucket_days
                            ),
                            Decimal("0"),
                        )
                    ),
                }
            )
            cursor = until
        submitted_agencies = AgencyVerificationSubmission.objects.filter(
            status="pending"
        )
        pending_profiles = AgencyProfile.objects.filter(verification_status="pending")
        never_submitted = pending_profiles.exclude(
            verification_submissions__isnull=False
        )
        statuses = list(
            requests.values("status").annotate(count=Count("id")).order_by("status")
        )
        queued_mail = PasswordRecoveryChallenge.objects.filter(
            user__isnull=False,
            used_at__isnull=True,
            emailed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        failed_mail = queued_mail.filter(delivery_attempts__gte=5).count()
        return Response(
            {
                "timezone": settings.TIME_ZONE,
                "currency": "TND",
                "start": start_day.isoformat(),
                "endExclusive": end_day.isoformat(),
                "requests": requests.count(),
                "requestingCustomers": requests.values("customer_id")
                .distinct()
                .count(),
                "rentalCollections": str(_amount(collections, "rental_amount")),
                "priorRentalCollections": str(
                    _amount(prior_collections, "rental_amount")
                ),
                "priorRequests": prior_requests.count(),
                "outstandingRental": str(
                    _amount(Payment.objects.filter(status="due"), "rental_amount")
                ),
                "paidDepositRecords": str(
                    _amount(Payment.objects.filter(status="paid"), "deposit_amount")
                ),
                "undatedPaidRecords": Payment.objects.filter(
                    status="paid", paid_at__isnull=True
                ).count(),
                "readyAgencyReviews": submitted_agencies.count(),
                "agenciesAwaitingDocuments": never_submitted.count(),
                "agencyReviewsOlder48h": submitted_agencies.filter(
                    submitted_at__lt=timezone.now() - timedelta(hours=48)
                ).count(),
                "customerReviewsOlder48h": CustomerVerificationSubmission.objects.filter(
                    status="pending",
                    submitted_at__lt=timezone.now() - timedelta(hours=48),
                ).count(),
                "overdueReturns": Booking.objects.filter(
                    status="active", return_at__lt=timezone.now()
                ).count(),
                "vehicleDocumentsDue": Car.objects.exclude(status="archived")
                .filter(
                    Q(insurance_expiry__lte=today + timedelta(days=30))
                    | Q(registration_expiry__lte=today + timedelta(days=30))
                )
                .count(),
                "queuedRecoveryEmails": queued_mail.count(),
                "failedRecoveryEmails": failed_mail,
                "buckets": buckets,
                "statuses": statuses,
            }
        )
