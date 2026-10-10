import apps.agencies.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("agencies", "0002_agency_review_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="agencyprofile",
            name="bio",
            field=models.TextField(
                blank=True,
                default="",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="agencyprofile",
            name="services",
            field=models.JSONField(
                blank=True,
                default=list,
            ),
        ),
        migrations.AddField(
            model_name="agencyprofile",
            name="profile_image",
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to="agency_profiles/",
            ),
        ),
        migrations.CreateModel(
            name="AgencyVerificationSubmission",
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
                ("attempt_number", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("superseded", "Superseded"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "business_registration",
                    models.FileField(
                        max_length=500,
                        upload_to=(
                            apps.agencies.models
                            .business_registration_upload_to
                        ),
                    ),
                ),
                (
                    "tax_identification",
                    models.FileField(
                        max_length=500,
                        upload_to=(
                            apps.agencies.models
                            .tax_identification_upload_to
                        ),
                    ),
                ),
                (
                    "responsible_person_cin_recto",
                    models.ImageField(
                        max_length=500,
                        upload_to=(
                            apps.agencies.models
                            .responsible_person_cin_recto_upload_to
                        ),
                    ),
                ),
                (
                    "responsible_person_cin_verso",
                    models.ImageField(
                        max_length=500,
                        upload_to=(
                            apps.agencies.models
                            .responsible_person_cin_verso_upload_to
                        ),
                    ),
                ),
                (
                    "address_proof",
                    models.FileField(
                        max_length=500,
                        upload_to=(
                            apps.agencies.models
                            .address_proof_upload_to
                        ),
                    ),
                ),
                (
                    "rejection_reason",
                    models.TextField(
                        blank=True,
                        default="",
                    ),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "agency_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verification_submissions",
                        to="agencies.agencyprofile",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name=(
                            "reviewed_agency_verification_submissions"
                        ),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-submitted_at",)},
        ),
        migrations.AddConstraint(
            model_name="agencyverificationsubmission",
            constraint=models.UniqueConstraint(
                fields=("agency_profile", "attempt_number"),
                name="ag_ver_profile_attempt_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="agencyverificationsubmission",
            index=models.Index(
                fields=["agency_profile", "status"],
                name="ag_ver_profile_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="agencyverificationsubmission",
            index=models.Index(
                fields=["status", "submitted_at"],
                name="ag_ver_status_sub_idx",
            ),
        ),
    ]
