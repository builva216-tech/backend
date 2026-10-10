import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContactVerificationChallenge",
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
                    "contact_type",
                    models.CharField(
                        choices=[
                            ("phone", "Phone"),
                            ("email", "Email"),
                        ],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                (
                    "pending_value",
                    models.CharField(max_length=254),
                ),
                (
                    "otp_hash",
                    models.CharField(max_length=128),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("verified", "Verified"),
                            ("expired", "Expired"),
                            ("locked", "Locked"),
                            ("superseded", "Superseded"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "attempts_remaining",
                    models.PositiveSmallIntegerField(default=5),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "expires_at",
                    models.DateTimeField(),
                ),
                (
                    "resend_available_at",
                    models.DateTimeField(),
                ),
                (
                    "verified_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contact_verification_challenges",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="contactverificationchallenge",
            index=models.Index(
                fields=["user", "contact_type", "status"],
                name="acct_contact_usr_type_st_idx",
            ),
        ),
    ]
