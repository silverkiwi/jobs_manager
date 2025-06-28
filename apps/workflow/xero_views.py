from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.workflow.models import XeroError
from apps.workflow.serializers import XeroErrorSerializer


class XeroErrorListAPIView(ListAPIView):
    queryset = XeroError.objects.all().order_by('-timestamp')
    serializer_class = XeroErrorSerializer


class XeroErrorDetailAPIView(RetrieveAPIView):
    queryset = XeroError.objects.all()
    serializer_class = XeroErrorSerializer
