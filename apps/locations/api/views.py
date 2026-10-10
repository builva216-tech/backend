from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from apps.locations.models import Governorate

from .serializers import GovernorateSerializer


class GovernorateListView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = GovernorateSerializer
    pagination_class = None

    def get_queryset(self):
        return Governorate.objects.filter(is_active=True).order_by(
            "display_order",
            "code",
        )
