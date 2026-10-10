import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models

import apps.customer_verifications.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerVerificationSubmission",
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
                    "attempt_number",
                    models.PositiveIntegerField(),
                ),
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
                    "cin_recto",
                    models.ImageField(
                        max_length=500,
                        upload_to=(
                            apps.customer_verifications.models
                            .cin_recto_upload_to
                        ),
                    ),
                ),
                (
                    "cin_verso",
                    models.ImageField(
                        max_length=500,
                        upload_to=(
                            apps.customer_verifications.models
                            .cin_verso_upload_to
                        ),
                    ),
                ),
                (
                    "selfie",
                    models.ImageField(
                        max_length=500,
                        upload_to=(
                            apps.customer_verifications.models
                            .selfie_upload_to
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
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=(
                            django.db.models.deletion.SET_NULL
                        ),
                        related_name=(
                            "reviewed_customer_verifications"
                        ),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name=(
                            "customer_verification_submissions"
                        ),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-submitted_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="customerverificationsubmission",
            constraint=models.UniqueConstraint(
                fields=("user", "attempt_number"),
                name="cust_ver_usr_attempt_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="customerverificationsubmission",
            index=models.Index(
                fields=["user", "status"],
                name="cust_ver_usr_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="customerverificationsubmission",
            index=models.Index(
                fields=["status", "submitted_at"],
                name="cust_ver_st_sub_idx",
            ),
        ),
    ]
