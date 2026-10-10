import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("agencies", "0003_verification_documents_and_public_profile"),
        ("fleet", "0001_initial"),
        ("locations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Booking",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("pickup_at", models.DateTimeField()),
                ("return_at", models.DateTimeField()),
                ("rental_days", models.PositiveIntegerField()),
                (
                    "daily_price_snapshot",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "base_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "extras_total",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "insurance_total",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "total_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "security_deposit",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "pickup_city",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=80,
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        default="cash",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("approved", "Approved"),
                            ("confirmed", "Confirmed"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="requested",
                        max_length=20,
                    ),
                ),
                (
                    "customer_note",
                    models.TextField(
                        blank=True,
                        default="",
                    ),
                ),
                (
                    "agency_note",
                    models.TextField(
                        blank=True,
                        default="",
                    ),
                ),
                (
                    "agency_responded_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "confirmed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "pickup_completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "returned_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "cancelled_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to="agencies.agencyprofile",
                    ),
                ),
                (
                    "car",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to="fleet.car",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="customer_bookings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pickup_governorate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="booking_pickups",
                        to="locations.governorate",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="BookingExtra",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "option_id_snapshot",
                    models.UUIDField(
                        blank=True,
                        null=True,
                    ),
                ),
                ("name", models.CharField(max_length=80)),
                ("pricing_type", models.CharField(max_length=20)),
                (
                    "unit_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "unit_cost",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1)),
                (
                    "total_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extras",
                        to="bookings.booking",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BookingInsurance",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "option_id_snapshot",
                    models.UUIDField(
                        blank=True,
                        null=True,
                    ),
                ),
                ("name", models.CharField(max_length=80)),
                (
                    "daily_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "daily_cost",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "total_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "security_deposit",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "booking",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="insurance",
                        to="bookings.booking",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BookingStatusEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=20,
                    ),
                ),
                ("to_status", models.CharField(max_length=20)),
                (
                    "note",
                    models.TextField(
                        blank=True,
                        default="",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="booking_status_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_events",
                        to="bookings.booking",
                    ),
                ),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["car", "status", "pickup_at", "return_at"],
                name="booking_car_status_range_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["agency", "status"],
                name="booking_agency_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["customer", "status"],
                name="booking_cust_status_idx",
            ),
        ),
    ]
