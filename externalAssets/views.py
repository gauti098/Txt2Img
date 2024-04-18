from django.conf import settings
from django.contrib.auth import authenticate, get_user_model

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.pagination import LimitOffsetPagination
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q



from externalAssets.models import (
    Icons,Elements,Shapes,
    Mask,Emoji
)


from externalAssets.serializers import (
    IconsSerializer,ElementsSerializer,ShapesSerializer,
    MaskSerializer,EmojiSerializer
)



class LimitOffset(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50


class IconsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = IconsSerializer

    def get(self, request, format=None):

        query = request.GET.get("q",None)
        if query:
            allQuery = Icons.objects.annotate(rank=SearchRank(SearchVector('name','tags'), SearchQuery(query))).order_by('-rank')
        else:
            allQuery = Icons.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)

class ShapesView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShapesSerializer

    def get(self, request, format=None):

        query = request.GET.get("q",None)
        if query:
            allQuery = Shapes.objects.annotate(rank=SearchRank(SearchVector('name','tags'), SearchQuery(query))).order_by('-rank')
        else:
            allQuery = Shapes.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


class ElementsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = ElementsSerializer

    def get(self, request, format=None):

        query = request.GET.get("q",None)
        if query:
            allQuery = Elements.objects.annotate(rank=SearchRank(SearchVector('name','tags'), SearchQuery(query))).order_by('-rank')
        else:
            allQuery = Elements.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


class EmojiView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmojiSerializer

    def get(self, request, format=None):

        query = request.GET.get("q",None)
        if query:
            allQuery = Emoji.objects.annotate(rank=SearchRank(SearchVector('name','tags'), SearchQuery(query))).order_by('-rank')
        else:
            allQuery = Emoji.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


class CommonView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmojiSerializer

    def get(self, request, format=None):
        _allData = {}
        allQuery = Emoji.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = EmojiSerializer(results, many=True,context={'request': request})
        _allData["emoji"] = self.get_paginated_response(serializer.data).data
        if _allData["emoji"]["next"]:
            _allData["emoji"]["next"] = _allData["emoji"]["next"].replace('common','emoji')

        allQuery = Elements.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = ElementsSerializer(results, many=True,context={'request': request})
        _allData["elements"] = self.get_paginated_response(serializer.data).data
        if _allData["elements"]["next"]:
            _allData["elements"]["next"] = _allData["elements"]["next"].replace('common','elements')

        allQuery = Shapes.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = ShapesSerializer(results, many=True,context={'request': request})
        _allData["shapes"] = self.get_paginated_response(serializer.data).data
        if _allData["shapes"]["next"]:
            _allData["shapes"]["next"] = _allData["shapes"]["next"].replace('common','shapes')

        allQuery = Icons.objects.all()
        results = self.paginate_queryset(allQuery, request, view=self)
        serializer = IconsSerializer(results, many=True,context={'request': request})
        _allData["icons"] = self.get_paginated_response(serializer.data).data
        if _allData["icons"]["next"]:
            _allData["icons"]["next"] = _allData["icons"]["next"].replace('common','icons')

        return Response(_allData,status=status.HTTP_200_OK)


class MaskView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MaskSerializer

    def get(self, request, format=None):

        allQuery = Mask.objects.all()
        serializer = self.serializer_class(allQuery, many=True,context={'request': request})
        content = {'results': serializer.data}
        return Response(content,status=status.HTTP_200_OK)