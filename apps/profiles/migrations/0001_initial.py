import apps.profiles.models
import django.db.models.deletion
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_contactverificationchallenge"),
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerProfile",
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
                    "city",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=80,
                    ),
                ),
                (
                    "profile_image",
                    models.ImageField(
                        blank=True,
                        max_length=500,
                        null=True,
                        upload_to=(
                            apps.profiles.models
                            .customer_profile_image_upload_to
                        ),
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "governorate",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="customer_profiles",
                        to="locations.governorate",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_profile",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"ordering": ("-updated_at",)},
        ),
    ]
