from django.conf import settings
from rest_framework import serializers, status

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q



class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50


from subscriptions.serializers import VideoCreditUsageSerializer

from subscriptions.models import VideoCreditUsage


class CreditDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoCreditUsageSerializer

    def get(self, request, format=None):

        queryset = VideoCreditUsage.objects.filter(user=request.user).order_by('-timestamp')
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)