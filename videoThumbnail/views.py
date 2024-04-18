from campaign.models import MainCampaign
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q

import os,re,json
from uuid import UUID,uuid1
import shutil

import logging
import traceback
logger = logging.getLogger(__name__)



from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob
from aiQueueManager.models import VideoRenderMultipleScene,Colors

class LimitOffset(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50


from videoThumbnail.serializers import (
    MainThumbnailSerializer,
    MainThumbnailListSerializer
    )
from videoThumbnail.models import MainThumbnail
from videoThumbnail.models import THUMBNAIL_CATEGORY
_THUMBNAIL_CATEGORY = [i[0] for i in THUMBNAIL_CATEGORY]


class ErrorCheck(APIView,LimitOffset):

    def get(self, request, format=None):
        t = 0/0
        return Response('ok')



class MainThumbnailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainThumbnailListSerializer

    def get(self, request, format=None):

        user = request.user
        data = request.GET
        query = data.get('query','')
        try:
            category = int(data.get('category',''))
            if category not in _THUMBNAIL_CATEGORY:
                category = ''
        except:
            category = ''

        currentAvatar = 4
        _videoId = data.get('id',None)
        _isCampaign = data.get('campaign',None)
        if _isCampaign:
            try:
                if int(_isCampaign):
                    _videoInst = MainCampaign.objects.get(id=_videoId,user=request.user)
                    currentAvatar = _videoInst.video.avatar_image.id
            except:
                pass
        else:
            if _videoId!=None:
                try:
                    _videoInst = VideoRenderMultipleScene.objects.get(id=int(_videoId),user=request.user)
                    currentAvatar = _videoInst.avatar_image.id
                except:
                    pass

        orderBy = data.get('order','')

        if query and category!='':
            if category == 1:
                queryset = MainThumbnail.objects.filter(name__icontains=query,category=category,currentAvatar=currentAvatar)
            else:
                queryset = MainThumbnail.objects.filter(user=user,name__icontains=query,category=category)
        elif category!='':
            if category == 1:
                queryset = MainThumbnail.objects.filter(category=category,currentAvatar=currentAvatar)
            else:
                queryset = MainThumbnail.objects.filter(user=user,category=category)
        elif query:
            queryset = MainThumbnail.objects.filter(user=user,name__icontains=query)
        else:
            queryset = MainThumbnail.objects.filter(user=user)

        # order
        # 0 => A-Z
        # 1 => Z-A
        # 2 => oldest updated
        # 3 => newest updated
        # 4 => oldest created
        # 5 => newest created

        if orderBy in ['0','1','2','3','4','5']:
            if orderBy == '0':
                queryset = queryset.order_by('name')
            elif orderBy == '1':
                queryset = queryset.order_by('-name')
            elif orderBy == '2':
                queryset = queryset.order_by('updated')
            elif orderBy == '3':
                queryset = queryset.order_by('-updated')
            elif orderBy == '3':
                queryset = queryset.order_by('timestamp')
            elif orderBy == '3':
                queryset = queryset.order_by('-timestamp')
            else:
                queryset = queryset.order_by('-updated')
        else:
            queryset = queryset.order_by('-updated')
            

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)

    def post(self, request, format=None):
        user = request.user
        data = request.data
        _name = data.get('name',None)
        _jsonData = data.get('jsonData',None)

        __inst = MainThumbnail.objects.filter(user=user,name__icontains='Untitled').order_by('-timestamp')
        if __inst.count()>0:
            __inst = __inst.last()
            try:
                _id = int(__inst.name.split('Untitled')[1])
            except:
                _id = 1
        else:
            _id = 1
        if not _name:
            _name = f'Untitled{_id}'
        mainInst = MainThumbnail(user = user,name = _name,category=2)
        if not _jsonData:
            _jsonData = mainInst.getDefaultData()

        mainInst.jsonData = _jsonData
        mainInst.save()
        if mainInst.jsonData:
            mainInst.updateThumbnail()
        content = {'result': MainThumbnailSerializer(mainInst,context={'request': request}).data}
        return Response(content,status=status.HTTP_201_CREATED)
        
class MainThumbnailDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainThumbnailSerializer

    def get_object(self, pk,user):
        try:
            _crntInst = MainThumbnail.objects.get(pk=pk)
            if _crntInst.user.pk == user.pk or _crntInst.isPublic:
                return (True,_crntInst)
            else:
                return (False,"")
        except MainThumbnail.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            responseData = self.serializer_class(inst,context={'request': request}).data
            content = {'result': responseData}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        

    def put(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        data = request.data
        if is_exist:
            if inst.category==2:
                _name = data.get('name',None)
                _jsonData = data.get('jsonData',None)

                _colors = data.pop("color",None)
                if _colors:
                    colorInst,ct = Colors.objects.get_or_create(user=user)
                    colorInst.setColors(_colors)

                isThumbnailUpdate = False
                if _name:
                    inst.name = _name
                if _jsonData:
                    if _jsonData != inst.jsonData:
                        inst.jsonData = _jsonData
                        isThumbnailUpdate = True

                inst.save()
                if isThumbnailUpdate:
                    inst.updateThumbnail()
                    _vm = VideoRenderMultipleScene.objects.filter(selectedThumbnail__pk=inst.pk)
                    for cvm in _vm:
                        cvm.setThumbnail()

                inst.replaceBase64ImageToFile()
                content = {'result': MainThumbnailSerializer(inst,context={'request': request}).data}
                return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Object is Not Editable'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self,request,pk):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if inst.category==2:
                inst.delete()
                content = {'detail': 'Object Deleted!'}
                return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Object is Not Deletable'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class ThumbnailViewColorsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainThumbnail.objects.get(pk=pk,user=user))
        except MainThumbnail.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if inst.userColors:
                allColor = [i for i in inst.userColors.split(',')[::-1] if i] + settings.VIDEO_DEFAULT_COLOR
            else:
                allColor = settings.VIDEO_DEFAULT_COLOR
            return Response({'color': allColor},status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        user = request.user
        value = request.data.get('color','')
        if value:
            if value[0] != '#':
                value = '#'+value
            is_exist,inst = self.get_object(pk,user)
            if is_exist:
                match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value)
                if match:
                    allColor = [i for i in inst.userColors.split(',')[::-1] if i] + settings.VIDEO_DEFAULT_COLOR
                    if value not in allColor:
                        if inst.userColors:
                            temp = inst.userColors.strip(',') + f",{value}"
                        else:
                            temp = f"{value}"
                        inst.userColors = temp.strip(',')
                        inst.save()
                    return Response('ok',status=status.HTTP_200_OK)
                else:
                    content = {'color': ['This Field is not Valid']}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)

        else:
            content = {'color': ['This Field is Required']}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)
        
