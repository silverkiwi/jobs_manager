from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Staff
from apps.accounts.permissions import IsSuperUser
from apps.accounts.serializers import StaffSerializer


class StaffListCreateAPIView(generics.ListCreateAPIView):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Staff.objects.all()


class StaffRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Staff.objects.all()
