from rest_framework import serializers

from apps.locations.models import Governorate


class GovernorateSerializer(serializers.ModelSerializer):
    nameAr = serializers.CharField(source="name_ar")
    nameFr = serializers.CharField(source="name_fr")
    nameEn = serializers.CharField(source="name_en")

    class Meta:
        model = Governorate
        fields = (
            "code",
            "nameAr",
            "nameFr",
            "nameEn",
        )
