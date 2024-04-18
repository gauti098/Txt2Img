from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

from django.db.models import Q

from videoCredit.models import UserCurrentSubscription,VideoCreditInfo
from videoCredit.serializers import CreditInfoSerilizer,VideoCreditInfoSerilizer


from utils.common import convertInt

class CreditInfoView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CreditInfoSerilizer

    def get(self, request, format=None):
        user = request.user
        inst,created = UserCurrentSubscription.objects.get_or_create(user=user)
        _subEnd = inst.isSubscriptionEnded()
        serializer = self.serializer_class(inst,context={'request': request})
        content = {'result': serializer.data,'isSubscriptionEnded': _subEnd}
        return Response(content,status=status.HTTP_200_OK)
        


class LimitOffset(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50


class CreditDetailsInfoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoCreditInfoSerilizer

    def get(self, request, format=None):

        data = request.GET
        creditType = convertInt(data.get('creditType',None),None)

        queryset = VideoCreditInfo.objects.filter(~Q(creditType=1),user=request.user).order_by('-timestamp')

        if creditType!=None:
            queryset = queryset.filter(creditType=creditType)
    
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)
