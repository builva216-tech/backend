import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("bookings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
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
                    "method",
                    models.CharField(
                        choices=[("cash", "Pay at agency / cash")],
                        default="cash",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("due", "Due"),
                            ("paid", "Paid"),
                            ("refunded", "Refunded"),
                        ],
                        db_index=True,
                        default="due",
                        max_length=20,
                    ),
                ),
                (
                    "rental_amount",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "deposit_amount",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "invoice_number",
                    models.CharField(
                        max_length=40,
                        unique=True,
                    ),
                ),
                (
                    "receipt_number",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "paid_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "refunded_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        default="",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment",
                        to="bookings.booking",
                    ),
                ),
                (
                    "collected_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="collected_payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
