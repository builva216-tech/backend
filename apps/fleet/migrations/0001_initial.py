import apps.fleet.models
import django.db.models.deletion
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("agencies", "0003_verification_documents_and_public_profile"),
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Car",
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
                ("brand", models.CharField(max_length=80)),
                ("model", models.CharField(max_length=80)),
                ("year", models.PositiveSmallIntegerField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("economy", "Economy"),
                            ("compact", "Compact"),
                            ("sedan", "Sedan"),
                            ("suv", "SUV"),
                            ("luxury", "Luxury"),
                            ("van", "Van"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "transmission",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("automatic", "Automatic"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "fuel_type",
                    models.CharField(
                        choices=[
                            ("petrol", "Petrol"),
                            ("diesel", "Diesel"),
                            ("hybrid", "Hybrid"),
                            ("electric", "Electric"),
                        ],
                        max_length=20,
                    ),
                ),
                ("seats", models.PositiveSmallIntegerField(default=5)),
                ("doors", models.PositiveSmallIntegerField(default=4)),
                (
                    "color",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=40,
                    ),
                ),
                (
                    "mileage_km",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "plate_number",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=32,
                    ),
                ),
                (
                    "daily_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=80,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=20,
                    ),
                ),
                (
                    "is_available",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                    ),
                ),
                (
                    "registration_expiry",
                    models.DateField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "insurance_expiry",
                    models.DateField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "condition_video",
                    models.FileField(
                        blank=True,
                        max_length=500,
                        null=True,
                        upload_to=apps.fleet.models.condition_video_upload_to,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cars",
                        to="agencies.agencyprofile",
                    ),
                ),
                (
                    "governorate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cars",
                        to="locations.governorate",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="CarPhoto",
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
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "image",
                    models.ImageField(
                        max_length=500,
                        upload_to=apps.fleet.models.car_photo_upload_to,
                    ),
                ),
                (
                    "car",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="fleet.car",
                    ),
                ),
            ],
            options={"ordering": ("position", "created_at")},
        ),
        migrations.CreateModel(
            name="AvailabilityBlock",
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
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                (
                    "reason",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=160,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "car",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="availability_blocks",
                        to="fleet.car",
                    ),
                ),
            ],
            options={"ordering": ("starts_at",)},
        ),
        migrations.CreateModel(
            name="ExtraOption",
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
                ("name", models.CharField(max_length=80)),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=240,
                    ),
                ),
                (
                    "pricing_type",
                    models.CharField(
                        choices=[
                            ("perDay", "Per day"),
                            ("oneTime", "One time"),
                        ],
                        default="perDay",
                        max_length=20,
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "estimated_cost",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_options",
                        to="agencies.agencyprofile",
                    ),
                ),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="InsuranceOption",
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
                ("name", models.CharField(max_length=80)),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=240,
                    ),
                ),
                (
                    "daily_price",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=12,
                    ),
                ),
                (
                    "estimated_daily_cost",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
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
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="insurance_options",
                        to="agencies.agencyprofile",
                    ),
                ),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddIndex(
            model_name="car",
            index=models.Index(
                fields=["status", "is_available"],
                name="fleet_car_status_avail_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="car",
            index=models.Index(
                fields=["governorate", "category"],
                name="fleet_car_gov_cat_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="availabilityblock",
            index=models.Index(
                fields=["car", "starts_at", "ends_at"],
                name="fleet_avail_car_range_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="extraoption",
            constraint=models.UniqueConstraint(
                fields=("agency", "name"),
                name="fleet_extra_agency_name_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="insuranceoption",
            constraint=models.UniqueConstraint(
                fields=("agency", "name"),
                name="fleet_ins_agency_name_uniq",
            ),
        ),
    ]
