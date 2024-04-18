from datetime import date
import time
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from moviepy.editor import *
from django.conf import settings
from glob import glob
import cv2
from moviepy.video.tools.drawing import circle



from appAssets.models import (
    AvatarImages,AvatarSounds,
    AvatarSoundCombination,
    VoiceLanguage
)

from appAssets.serializers import (
    AvatarImagesSerializer,
    AvatarSoundsSerializer,
    AvatarSoundCombinationSerializer,
    VoiceLanguageSerializer
)

from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q


class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50




class VoiceLanguageView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VoiceLanguageSerializer
    QUERY_CACHE = None

    def getVoiceLangQuery(self):
        if self.QUERY_CACHE == None:
            lang_ids = AvatarSounds.objects.all().exclude(provider = 'google').values_list('voice_language', flat=True)
            self.QUERY_CACHE = VoiceLanguage.objects.filter(pk__in=lang_ids).order_by("name")
        return self.QUERY_CACHE

    def get(self, request, format=None):
        
        query = request.GET.get("q",None)
        allQuery = self.getVoiceLangQuery()#VoiceLanguage.objects.all().order_by("name")
        if query:
            allQuery = allQuery.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(country__name__icontains=query) | Q(country__code__icontains=query) | Q(tags__icontains=query))
        country = request.GET.get("country",None)
        if country:
            allQuery = allQuery.filter(Q(country__name__icontains=country) | Q(country__code__icontains=country))
        name = request.GET.get("name",None)
        if name:
            allQuery = allQuery.filter(Q(name__icontains=name))

        serializer = self.serializer_class(allQuery.distinct(), many=True,context={'request': request})
        content = {'result': serializer.data}
        return Response(content,status=status.HTTP_200_OK)


class GetAvatarVoicesView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AvatarSoundsSerializer

    def post(self, request, format=None):
        
        avatarId = request.data.get("avatarId",None)
        languageId = request.data.get("languageId",None)
        
        if avatarId:
            try:
                _avatarInst = AvatarImages.objects.get(id=int(avatarId))
            except:
                content = {"message": "avatarId is not Valid."}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {"message": "avatarId is required."}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)

        if languageId:
            try:
                _languageInst = VoiceLanguage.objects.get(id=int(languageId))
            except:
                content = {"message": "languageId is not Valid."}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {"message": "languageId is required."}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)


        soundQuery = AvatarSounds.objects.filter(voice_language=_languageInst).exclude(provider='google')
        _maleQuery = soundQuery.filter(gender=1)
        _femaleQuery = soundQuery.filter(gender=2)
        _maleQueryC = _maleQuery.count()
        _femaleQueryC = _femaleQuery.count()
        _otherData = None
        if _avatarInst.gender == 1:
            avatarSound = self.serializer_class(_maleQuery, many=True,context={'request': request}).data
            if _maleQueryC==0:
                _otherData = self.serializer_class(_femaleQuery, many=True,context={'request': request}).data
        else:
            avatarSound = self.serializer_class(_femaleQuery, many=True,context={'request': request}).data
            if _femaleQueryC==0:
                _otherData = self.serializer_class(_maleQuery, many=True,context={'request': request}).data
        content = {'results': avatarSound,'genderVoiceCount': {1: _maleQueryC,2: _femaleQueryC},'otherData': _otherData}

        return Response(content,status=status.HTTP_200_OK)


class AvatarsImagesView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = AvatarImagesSerializer

    def get(self, request, format=None):
        
        queryset = AvatarImages.objects.all()
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


class AvatarsImagesDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = AvatarImagesSerializer

    def get_object(self, pk):
        try:
            return (True,AvatarImages.objects.get(pk=pk))
        except AvatarImages.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk)
        if is_exist:
            serializer = self.serializer_class(inst,context={'request': request})
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        
class AvatarsSoundView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = AvatarSoundsSerializer

    def get(self, request, format=None):


        queryset = AvatarSounds.objects.all()
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)
        

class AvatarsSoundDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = AvatarSoundsSerializer

    def get_object(self, pk):
        try:
            return (True,AvatarSounds.objects.get(pk=pk))
        except AvatarImages.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk)
        if is_exist:
            serializer = self.serializer_class(inst,context={'request': request})
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class AvatarSoundCombinationView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = AvatarSoundCombinationSerializer

    def get(self, request, format=None):
        avatarCombinationQuery = AvatarSoundCombination.objects.all()
        avatarCombination = AvatarSoundCombinationSerializer(avatarCombinationQuery, many=True,context={'request': request}).data
        avatarCombinationT = {}
        for avc in avatarCombination:
            avatarCombinationT[f"{avc['avatarImg']}_{avc['avatarSound']}"] = avc
        return Response({"results": avatarCombinationT},status=status.HTTP_200_OK)



