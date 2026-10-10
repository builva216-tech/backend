from apps.agencies.subscriptions import require_management
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAgency
from apps.agencies.models import AgencyCustomerRecord, AgencyProfile
from apps.bookings.models import Booking
from apps.fleet.services import require_approved_agency


class CrmTaskSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=80)
    title = serializers.CharField(max_length=160)
    due = serializers.DateField()
    completed = serializers.BooleanField(default=False)

    def validate_due(self, value):
        if not 2000 <= value.year <= 2100:
            raise serializers.ValidationError("Select a date between 2000 and 2100.")
        return value


class CrmWriteSerializer(serializers.Serializer):
    agencyId = serializers.UUIDField(required=False)
    expectedRevision = serializers.IntegerField(min_value=0)
    alias = serializers.CharField(max_length=80, allow_blank=True, required=False)
    notes = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    tags = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["VIP", "Business", "Family", "Follow up"]
        ),
        max_length=4,
        required=False,
    )
    tasks = CrmTaskSerializer(many=True, required=False)

    def validate_tasks(self, values):
        if len(values) > 100 or len({value["id"] for value in values}) != len(values):
            raise serializers.ValidationError("Use at most 100 tasks with unique IDs.")
        return values


def record_payload(record):
    return {
        "customerId": str(record.customer_id),
        "alias": record.alias,
        "notes": record.notes,
        "tags": record.tags,
        "tasks": record.tasks,
        "revision": record.revision,
        "updatedAt": record.updated_at.isoformat(),
    }


class AgencyCrmListView(APIView):
    permission_classes = (IsAgency,)

    def get(self, request):
        agency = require_approved_agency(request.user)
        if request.query_params.get("agencyId") and request.query_params[
            "agencyId"
        ] != str(request.user.id):
            raise NotFound("Agency workspace not found.")
        customers = Booking.objects.filter(agency=agency).values("customer_id")
        records = AgencyCustomerRecord.objects.filter(
            agency=agency, customer_id__in=customers
        ).order_by("customer_id")
        return Response([record_payload(record) for record in records])


class AgencyCrmRecordView(APIView):
    permission_classes = (IsAgency,)

    def _relationship(self, request, customer_id):
        agency = require_approved_agency(request.user)
        if not Booking.objects.filter(agency=agency, customer_id=customer_id).exists():
            raise NotFound("Customer relationship not found.")
        return agency

    def get(self, request, customer_id):
        agency = self._relationship(request, customer_id)
        record = get_object_or_404(
            AgencyCustomerRecord, agency=agency, customer_id=customer_id
        )
        return Response(record_payload(record))

    def patch(self, request, customer_id):
        require_management(request.user.agency_profile)
        agency = self._relationship(request, customer_id)
        serializer = CrmWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if "agencyId" in values and values["agencyId"] != request.user.id:
            raise NotFound("Agency workspace not found.")
        with transaction.atomic():
            # Serialize creation as well as updates; revisions prevent silent lost edits.
            AgencyProfile.objects.select_for_update().get(id=agency.id)
            record, _ = AgencyCustomerRecord.objects.get_or_create(
                agency=agency, customer_id=customer_id
            )
            if values["expectedRevision"] != record.revision:
                return Response(
                    {
                        "detail": "Customer notes changed elsewhere. Review the latest record before saving again.",
                        "currentRecord": record_payload(record),
                    },
                    status=409,
                )
            for field in ["alias", "notes", "tags", "tasks"]:
                if field in values:
                    value = values[field]
                    if field == "tasks":
                        value = [
                            {**task, "due": task["due"].isoformat()} for task in value
                        ]
                    if field == "tags":
                        value = list(dict.fromkeys(value))
                    setattr(record, field, value)
            record.revision += 1
            record.save()
        return Response(record_payload(record))
