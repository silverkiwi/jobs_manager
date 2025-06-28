from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.workflow.api.pagination import FiftyPerPagePagination
from apps.workflow.models import XeroError
from apps.workflow.serializers import XeroErrorSerializer


class XeroErrorListAPIView(ListAPIView):
    queryset = XeroError.objects.all().order_by('-timestamp')
    serializer_class = XeroErrorSerializer
    pagination_class = FiftyPerPagePagination


class XeroErrorDetailAPIView(RetrieveAPIView):
    queryset = XeroError.objects.all()
    serializer_class = XeroErrorSerializer
