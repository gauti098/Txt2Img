from shutil import copy
from uuid import uuid4
from django.conf import settings
from rest_framework import serializers, status

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
import json,traceback
import logging
from backgroundclip.models import APISaveVideo
from backgroundclip.serializers import APISaveVideoServerSideSerializer
from campaign.models import EmailClient
from newImageEditor import models as newImageEditorModels
from newImageEditor import serializers as newImageEditorSerializers
from newVideoCreator.utils.validateMergeTag import validateMtag
from salesPage.models import SalesPageEditor
from salesPage import serializers as salesPageSerilaizers
from campaign import serializers as campaignSerilaizers

from newVideoCreator import task as newVideoCreatorTask

from utils.common import convertInt
from events import fire


logger = logging.getLogger(__name__)

from newVideoCreator.models import (
    EmailGenTracker, GroupHandler, TempVideoCreator,VideoAnimation,
    VideoFilter,VideoTemplate,VideoSceneAnimation,
    TextAnimation,MainVideoGenerate,
    AiVideoSceneGenerate,
    FontFamily,THUMBNAIL_TYPE
)
from newVideoCreator.serializers import (
    BatchMailMinSerializer, EmailGenerateHistorySerializer, MainVideoGenerateCampaignSerializer, MainVideoGenerateSerializer, MainVideoGenerateWithMergeTagSerializer, TempVideoCreatorSerializer,TempVideoCreatorDetailsSerializer,
    VideoAnimationSerializer,VideoFilterSerializer,
    VideoTemplateSerializer,VideoCreatorSerializer,VideoSceneAnimationSerializer,
    VideoDetailsSerializer,TextAnimationSerializer,
    VideoVerticalTemplateSerializer,VideoSquareTemplateSerializer,
    VideoHorizontalTemplateSerializer,
    FontFamilySerializer,MainVideoGenerateSoloMailSerializer,
    BatchGeneratedHistoryFileSerializer
)
from videoThumbnail.models import MainThumbnail


import time,os
from django.db.models import Q
from threading import Thread
import traceback
from django.utils import timezone


'''
AI_STATUS = (
    (0,'ERROR'),

    (2,'RUNNING'),
    (3,'PENDING'),

    (1,'COMPLETED'),
)
'''
if settings.LOAD_GPU_MODEL:
    from AiHandler.utils import (
        getVideoGenerateConfig,mainVideoGenerate,
        getMelChunks
    )
## Generate Video Thread
def generateAiVideo():
    time.sleep(20)
    # app start time
    try:
        resQuery = MainVideoGenerate.objects.filter(Q(status=0) | Q(status=2))
        for _query in resQuery:
            _query.status = 3
            _query.save()
        while True:
            try:
                query = MainVideoGenerate.objects.filter(status=3,isSetupCompleted=True)
                if query.count()==0:
                    time.sleep(10)
                    continue
            except:
                time.sleep(10)
                continue
            
            try:
                _crntQuery = query.first()
                _crntQuery.status = 2
                _crntQuery.save()

                # update status for batch mail
                if _crntQuery.groupHandlerTracker:
                    if _crntQuery.groupHandlerTracker.status == 3:
                        _crntQuery.groupHandlerTracker.status = 2
                        _crntQuery.groupHandlerTracker.save()
                        _crntQuery.groupHandlerTracker.updateProgress()
                else:
                    _crntQuery.updateProgress()

                _sceneArr = json.loads(_crntQuery.videoCreator.parseData)["sceneArr"]
                _totalScene = len(_sceneArr)

                allAiVideo = []
                _completed = 0
                for _sceneIndex in _sceneArr:
                    _aiSceneInst = _crntQuery.aiSceneGenerate.get(sceneIndex=int(_sceneIndex))
                    queue_inst = _aiSceneInst.aiTask
                    if queue_inst and queue_inst.status != 1:
                        allAiVideo.append([queue_inst,_aiSceneInst])
                    else:
                        _completed+=1
                        _aiSceneInst.onComplete(completedScene=_completed,totalScene=_totalScene)

                for queue_inst,_aiSceneInst in allAiVideo:
                    # generate sound
                    isSound = queue_inst.fullAudioPath
                    if isSound:
                        queue_inst.status = 2
                        isMelChunk,mel_chunks = getMelChunks(isSound.path)
                        if isMelChunk:
                            queue_inst.totalOutputFrame = len(mel_chunks)
                            queue_inst.save()
                            wav2lipConfig,avatarConfig = getVideoGenerateConfig(queue_inst,mel_chunks=mel_chunks)
                            mainVideoGenerate(wav2lipConfig,avatarConfig)
                            queue_inst.status = 1
                            queue_inst.save()
                        else:
                            queue_inst.logs = "Mel Chunks not generated."
                            queue_inst.status = 0
                            queue_inst.save()
                    else:
                        queue_inst.status = 1
                        queue_inst.save()

                    _completed+=1
                    _aiSceneInst.onComplete(completedScene=_completed,totalScene=_totalScene)

                _crntQuery.onAiComplete()
            except Exception as e:
                logger.error(f"NewVideoCreator generateAiVideo: {str(traceback.format_exc())}")
                open('/home/govind/data.log','a').write(f"Some Error Occured: {e} {str(traceback.format_exc())}\n")
                time.sleep(20)
    except Exception as e:
        open('/home/govind/data.log','a').write(f"Some Error Occured: {e} {str(traceback.format_exc())}\n")
        time.sleep(20)

if settings.LOAD_GPU_MODEL:
    logger.info('Started AI Generate... ')
    aiT = Thread(target=generateAiVideo)
    aiT.daemon = True
    aiT.start()



class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50

class VideoTemplateView(APIView,LimitOffset):
    permission_classes = (AllowAny,)
    serializer_class = VideoTemplateSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','')
        filter = data.get('q','')
        isHuman = data.get('human',None)
        if isHuman:
            isHuman = 1
        else:
            isHuman = 0

        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        queryset = VideoTemplate.objects.filter(isHuman=isHuman)
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(name__icontains=filter)

        if isOrder != None:
            queryset = queryset.order_by(isOrder)
    
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class DraftVideoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoCreatorSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','3')
        filter = data.get('q','')


        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        queryset = TempVideoCreator.objects.filter(user=request.user,mainVideoGenerate__isnull=True)
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(name__icontains=filter)

        if isOrder != None:
            queryset = queryset.order_by(isOrder)
    
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class CopyVideoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get(self, request,pk, format=None):

        isValid,_inst = TempVideoCreator.isValidUser(request.user,pk)
        if isValid:
            _new= TempVideoCreator(user=request.user,name=f"Copy of {_inst.name}",jsonData=_inst.jsonData)
            _new.save()
            _thumbnailP,_thumbnailN = _new.getThumbnailPath()
            _isError = False
            try:
                copy(_inst.thumbnail.path,_thumbnailP)
            except:
                _isError = True
            _new.thumbnail.name = _thumbnailN
            _new.save()
            # _newJsonData = _inst.changeJsonDataId(_new.id)
            # if _newJsonData[0]:
            #     _new.jsonData = _newJsonData[1]
            #     _new.save()
            if _isError:
                _new.updateDraftThumbnail()

            content = {'result': {'id': _new.id}}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class GeneratedVideoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoCreatorSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','')
        filter = data.get('q','')


        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp',6: 'generatedAt',7: '-generatedAt'}
        isOrder = None
        queryset = TempVideoCreator.objects.filter(user=request.user,mainVideoGenerate__isnull=False).order_by('-generatedAt')
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(name__icontains=filter)

        if isOrder != None:
            queryset = queryset.order_by(isOrder)
    
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class TempVideoCreatorView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TempVideoCreatorSerializer

    def post(self, request, format=None):
        user = request.user
        _jsonData = request.data.get("d","")
        _name = request.data.get("name","")
        try:
            _jsonData = json.dumps(json.loads(_jsonData))
            _inst = TempVideoCreator(user=user,jsonData=_jsonData)
            if _name:
                _inst.name = _name
            _inst.save()
            _inst.updateDraftThumbnail()
            content = {"result": self.serializer_class(_inst,context={'request': request}).data}
            return Response(content,status=status.HTTP_200_OK)
        except:
            content = {"message": "Data is not Valid"}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)
        


class VideoCreatorDetailsView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoDetailsSerializer
    _VALID_THUBMNAIL_TYPE = [ii[0] for ii in THUMBNAIL_TYPE]
    
    def get_object(self, pk,user):
        try:
            return (True,TempVideoCreator.objects.get(pk=pk,user=user))
        except TempVideoCreator.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            sData = self.serializer_class(inst,context={'request': request}).data
            content = {'result': sData}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            _data = request.data

            if not inst.mainVideoGenerate:
                return Response({"message": 'Cannot Update Video Without Generate.'},status=status.HTTP_400_BAD_REQUEST)

            ## update thumbnail
            _thumbnailType = _data.get("thumbnailType",None)
            _thumbnailId = convertInt(_data.get("thumbnailId",None),None)
            if _thumbnailType!=None and _thumbnailId!=None:
                if _thumbnailId == inst.thumbnailInst.id:
                    _allMTag = json.loads(inst.allMergeTag)
                    content = {"allMergeTag": _allMTag,"isError": False}
                    return Response(content,status=status.HTTP_200_OK) 
                if _thumbnailType in self._VALID_THUBMNAIL_TYPE:
                    try:
                        _tinst = newImageEditorModels.ImageCreator.objects.get(id=_thumbnailId)
                        if (_tinst.user.id==user.id or _tinst.isTemplate) and (_tinst.isGenerated or _tinst.isAutoGenerated):
                            inst.thumbnailInst = _tinst
                            if _tinst.isTemplate:
                                _thumbnailType = 1
                            elif _tinst.isAutoGenerated:
                                _thumbnailType = 0
                            else:
                                _thumbnailType = 2
                            inst.thumbnailType = _thumbnailType
                            #inst.thumbnail.name = _tinst.thumbnail.name
                            inst.save()
                            inst.updateAllMergeTag()
                            _allMTag = json.loads(inst.allMergeTag)
                            content = {"allMergeTag": _allMTag,"isError": False}
                            commandData = {'id': inst.id,'results': {"thumbnailInst": newImageEditorSerializers.ImageCreatorSerializer(_tinst,context={'request': request}).data,"allMergeTag": _allMTag}}
                            fire.eventFire(user,"videoEditor.details.update",commandData)
                            return Response(content,status=status.HTTP_200_OK)
                        else:
                            content = {"thumbnailId": ['This Field is not Valid.'],"isError": True}
                            return Response(content,status=status.HTTP_200_OK)
                    except:
                        content = {"thumbnailId": ['This Field is not Valid.'],"isError": True}
                        return Response(content,status=status.HTTP_200_OK)
                else:
                    content = {"thumbnailType": ['This Field is not Valid.'],"isError": True}
                    return Response(content,status=status.HTTP_200_OK)
            elif _thumbnailType!=None:
                content = {"thumbnailType": ['This Field is not Valid.'],"isError": True}
                return Response(content,status=status.HTTP_200_OK)
            elif _thumbnailId!=None:
                content = {"thumbnailId": ['This Field is not Valid.'],"isError": True}
                return Response(content,status=status.HTTP_200_OK)
            

            ## handle sharing page
            _sharingPageId = convertInt(_data.get("sharingPageId",None),default=None)
            if _sharingPageId!=None:
                if _sharingPageId == inst.sharingPage.id:
                    _allMTag = json.loads(inst.allMergeTag)
                    content = {"allMergeTag": _allMTag,"isError": False}
                    return Response(content,status=status.HTTP_200_OK) 
                try:
                    _sInst = SalesPageEditor.objects.get(id=_sharingPageId,user=user,isPublish=True,appType=1)
                    inst.sharingPage = _sInst
                    inst.save()
                    inst.updateAllMergeTag()
                    _allMTag = json.loads(inst.allMergeTag)
                    content = {"allMergeTag": _allMTag,"isError": False}
                    commandData = {'id': inst.id,'results': {"sharingPage": salesPageSerilaizers.SalesPageListSerializer(_sInst,context={'request': request}).data,"allMergeTag": _allMTag}}
                    fire.eventFire(user,"videoEditor.details.update",commandData)
                    return Response(content,status=status.HTTP_200_OK)
                except:
                    content = {"sharingPageId": ['This Field is not Valid.'],"isError": True}
                    return Response(content,status=status.HTTP_200_OK)
           
            # update mail client
            _mailClient = _data.get('mailClient',None)
            if _mailClient:
                try:
                    _mailClientInst = EmailClient.objects.get(id=_mailClient)
                    inst.mailClient = _mailClientInst
                    inst.save()
                    commandData = {'id': inst.id,'results': {"mailClient": campaignSerilaizers.EmailClientSerializer(_mailClient,context={'request': request}).data}}
                    fire.eventFire(user,"videoEditor.details.update",commandData)
                except:
                    content = {"mailClient": ['This Field is not Valid.'],"isError": True}
                    return Response(content,status=status.HTTP_200_OK)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



def updateThumbnailOnSave(_id):
    try:
        _inst = TempVideoCreator.objects.get(id=_id)
        _updatedDiff = timezone.now() - _inst.updated
        if _updatedDiff.seconds>50:
            time.sleep(2)
            _inst.updateDraftThumbnail()
    except Exception as e:
        logger.error(f"Unable To Update Draft Thumbnail: {e} {str(traceback.format_exc())}" )


def replaceVideoWithHighQuality(inst,jsonData,request):
    allSceneIndex = inst.getSceneArray(jsonData["currentScene"])
    for _sceneIndex in allSceneIndex:
        _sceneData = jsonData[_sceneIndex]["jsonData"]["objects"]
        for n,_obj in enumerate(_sceneData):
            if inst.isVideo(_obj):
                _Video = _obj.get("_Video",{})
                if _Video:
                    _id = _Video.get("id",None)
                    if _id:
                        try:
                            _inst = APISaveVideo.objects.get(id=_id)
                            jsonData[_sceneIndex]["jsonData"]["objects"][n]["_Video"] = APISaveVideoServerSideSerializer(_inst,context={'request': request}).data
                        except Exception as e:
                            pass
        _sanimation = jsonData[_sceneIndex].get("sanimation",{})
        if _sanimation:
            _animationD = _sanimation.get("animationData",{})
            if _animationD:
                _loadAsset = _animationD.get("loadAsset",{})
                if _loadAsset:
                    _id = _loadAsset.get("id",None)
                    try:
                        _inst = APISaveVideo.objects.get(id=_id)
                        _data = APISaveVideoServerSideSerializer(_inst,context={'request': request}).data
                        _prevDict = jsonData[_sceneIndex]["sanimation"]["animationData"]["loadAsset"].copy()
                        _prevDict.update(_data)
                        jsonData[_sceneIndex]["sanimation"]["animationData"]["loadAsset"] = _prevDict
                    except Exception as e:
                        pass
    return jsonData



class TempVideoCreatorDetailView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = TempVideoCreatorDetailsSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id:
                return (True,_inst)
            elif _token == settings.SERVER_TOKEN:
                return (2,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            sData = self.serializer_class(inst,context={'request': request}).data
            # if server then replace _Video and loadAssests
            if is_exist==2:
                # process sData
                #sData = sData.copy()
                try:
                    sData["_videoData"] = json.loads(inst._videoData)#replaceVideoWithHighQuality(inst,sData["jsonData"],request)
                except:
                    pass
            content = {'result': sData}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _jsonData = request.data.get("d",None)
            _name = request.data.get("name","")
            if _name:
                inst.name = _name
            if _jsonData:
                if inst.mainVideoGenerate:
                    return Response({"message": 'Cannot Update Video After Generate.'},status=status.HTTP_400_BAD_REQUEST)
                inst.jsonData = _jsonData
            inst.save() 
            return Response("OK",status=status.HTTP_200_OK)
        else:
            content = {'message': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        
    def put(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _jsonData = request.data.get("d",None)
            _name = request.data.get("name","")
            if _name:
                inst.name = _name
                inst.save()
            if _jsonData:
                if inst.mainVideoGenerate:
                    return Response({"message": 'Cannot Update Video After Generate.'},status=status.HTTP_400_BAD_REQUEST)
                try:
                    _statusCode,_resData = inst.update_jsonData(_jsonData)
                    if _statusCode>=500:
                        logger.error(str(_resData))
                    if _statusCode<300:
                        _updateThumbnailThread = Thread(target=updateThumbnailOnSave,args=(inst.id,))
                        _updateThumbnailThread.start()
                        return Response(True,status=status.HTTP_200_OK)
                    else:
                        return Response(False,status=status.HTTP_200_OK)
                except:
                    return Response({"message": str(traceback.format_exc())},status=status.HTTP_503_SERVICE_UNAVAILABLE)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'message': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self,request,pk):
        is_exist,inst = self.get_object(pk,request)

        if is_exist:
            name = inst.name
            if inst.mainVideoGenerate:
                commandData = {"id": inst.id,'isGenerated': True}
            else:
                commandData = {"id": inst.id,'isGenerated': False}

            inst.delete()
            fire.eventFire(inst.user,"videoEditor.list.remove",commandData)
            content = {'name': name,'isError': False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': False}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class VideoAnimationView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoAnimationSerializer
    
    def get(self, request, format=None):
        _animationInOutQuery = VideoAnimation.objects.filter(category=0)
        _animationInPlaceQuery = VideoAnimation.objects.filter(category=1)
        content = {'results': self.serializer_class(_animationInOutQuery,many=True,context={'request': request}).data}
        content["inPlace"] = self.serializer_class(_animationInPlaceQuery,many=True,context={'request': request}).data
        return Response(content,status=status.HTTP_200_OK)


class TextAnimationView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TextAnimationSerializer
    
    def get(self, request, format=None):
        _charQuery = TextAnimation.objects.filter(category=0)
        _wordQuery = TextAnimation.objects.filter(category=1)
        _lineQuery = TextAnimation.objects.filter(category=2)
        #content = {'results': self.serializer_class(_animationQuery,many=True,context={'request': request}).data}
        content = {'result': {"char": self.serializer_class(_charQuery,many=True,context={'request': request}).data,"word": self.serializer_class(_wordQuery,many=True,context={'request': request}).data,"line": self.serializer_class(_lineQuery,many=True,context={'request': request}).data}}
        return Response(content,status=status.HTTP_200_OK)


class VideoSceneAnimationView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoSceneAnimationSerializer
    
    def get(self, request, format=None):
        _animationQuery = VideoSceneAnimation.objects.filter(category=0).order_by('-_order','category','name')
        content = {'results': self.serializer_class(_animationQuery,many=True,context={'request': request}).data}
        return Response(content,status=status.HTTP_200_OK)



class VideoFilterView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoFilterSerializer
    
    def get(self, request, format=None):
        _animationQuery = VideoFilter.objects.all()
        content = {'results': self.serializer_class(_animationQuery,many=True,context={'request': request}).data}
        return Response(content,status=status.HTTP_200_OK)


from userlibrary.models import FileUpload

class TotalUsedUploadFileView(APIView):
    permission_classes = (IsAuthenticated,)
    
    def get_object(self, pk,user):
        try:
            return (True,FileUpload.objects.get(pk=pk,user=user))
        except FileUpload.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            allInst = TempVideoCreator.objects.filter(user=user,jsonData__contains=inst.media_file.url)
            content = {'totalUsed': allInst.count()}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob

class GenerateVideoView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = TempVideoCreatorDetailsSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id:
                return (True,_inst)
            elif _token == settings.SERVER_TOKEN:
                return (1,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if is_exist == 1:
                if inst.mainVideoGenerate:
                    inst.mainVideoGenerate.delete()
                _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst)
                inst.mainVideoGenerate = _gInst
                inst.save()
                
                return Response(_gInst.generateVideo(isForced=True),status=status.HTTP_200_OK)
            else:
                _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst)
                if ct:
                    inst.mainVideoGenerate = _gInst
                    inst.save()
                    #newVideoCreatorTask.addVideoToGenerate.delay(f"{_gInst.id}")
                    _gInst.generateVideo()
                else:
                    if inst.mainVideoGenerate != _gInst:
                        inst.mainVideoGenerate = _gInst
                        inst.save()
            # commandData = VideoCreatorSerializer(inst,context={'request': request}).data
            # fire.eventFire(inst.user,"videoEditor.list.add",commandData)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _name = request.data.get("name",None)
            if _name:
                inst.name = _name
                inst.save()

            _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst)
            if ct:
                inst.mainVideoGenerate = _gInst
                inst.save()
                #newVideoCreatorTask.addVideoToGenerate.delay(f"{_gInst.id}")
                _gInst.generateVideo()
            else:
                if inst.mainVideoGenerate != _gInst:
                    inst.mainVideoGenerate = _gInst
                    inst.save()
            # commandData = VideoCreatorSerializer(inst,context={'request': request}).data
            # fire.eventFire(inst.user,"videoEditor.list.add",commandData)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class RenderVideoView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = TempVideoCreatorDetailsSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            rabbitMQSendJob('newVideoCreatorJob',json.dumps({"id": pk}),durable=True)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


def onCompleteRender(sceneIndex,isSuccess):
    try:
        _inst = AiVideoSceneGenerate.objects.get(pk=sceneIndex)
        _inst.onRenderComplete()
    except:
        pass
    return True

class RenderCompleteVideoView(APIView):
    permission_classes = (AllowAny,)
    
    def get_object(self,request):
        try:
            _token = request.GET.get('token',None)
            if _token == settings.SERVER_TOKEN:
                return (True,True)
            return (False,None)
        except:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(request)
        _isSuccess = request.GET.get('success',1)
        if is_exist:
            newVideoCreatorTask.sceneRenderComplete.apply_async(args=(pk,{},),countdown=10)
            # th = Thread(target=onCompleteRender,args=(pk,_isSuccess,))
            # th.start()
            return Response({'status': True},status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(request)
        _isSuccess = request.GET.get('success',1)
        if is_exist:
            _reqData = request.data.get("data",{})
            newVideoCreatorTask.sceneRenderComplete.apply_async(args=(pk,_reqData,),countdown=10)
            return Response({'status': True},status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class ThumbnailUpdateCallbackView(APIView):
    permission_classes = (AllowAny,)
    
    def get_object(self,request,pk):
        try:
            _token = request.GET.get('token',None)
            if _token == settings.SERVER_TOKEN or request.user:
                _inst = TempVideoCreator.objects.get(id=pk)
                return (True,_inst)
            elif request.user:
                _inst = TempVideoCreator.objects.get(user=request.user,id=pk)
                return (True,_inst)
            return (False,None)
        except:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(request,pk)
        if is_exist:
            commandData = {'id': pk,'results': {"thumbnail": inst.thumbnail.url}}
            fire.eventFire(inst.user,"videoEditor.details.update",commandData)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class UpdateVideoDraftThumbnailView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = TempVideoCreatorDetailsSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        sceneId = convertInt(request.GET.get('scene',0),default=0)
        if is_exist:
            # send message To Queue
            inst.updateDraftThumbnail(scene=sceneId)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _inst.updateDraftThumbnail(scene=0)
        except:
            pass
        return Response(True,status=status.HTTP_200_OK)
        


class VideoSceneView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = TempVideoCreatorDetailsSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN or TempVideoCreator.isValidUser(user,_inst.id)[0]:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            allScenes = []
            try:
                _crntData = json.loads(inst.jsonData)
                _sceneArr = json.loads(_crntData["currentScene"]["arr"])
                _sceneIdArr = request.GET.get('scene',None)
                
                if _sceneIdArr == None:
                    for sceneId in _sceneArr:
                        _ctData = _crntData[str(sceneId)]
                        _ctData['sceneIndex'] = sceneId
                        allScenes.append(_ctData)
                else:
                    for _scId in _sceneIdArr.split('_'):
                        _ctData = _crntData.get(_scId,None)
                        if _ctData!=None:
                            _ctData['sceneIndex'] = convertInt(_scId)
                            allScenes.append(_ctData)
            except Exception as e:
                logger.error(f"Unable To Parse VideoSceneView: {e} {str(traceback.format_exc())}" )
            return Response({"results": allScenes},status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class InsideVideoTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    
    def get(self, request, format=None):
        size=request.GET.get("size","16:9")
        _query = request.GET.get('q','')
        isHuman = convertInt(request.GET.get('human',None),None)

        if size == "1:1":
            if _query:
                queryset = VideoTemplate.objects.filter(sVideo__isnull=False,name__icontains =_query)
            else:
                queryset = VideoTemplate.objects.filter(sVideo__isnull=False)
            if isHuman!=None:
                queryset = queryset.filter(isHuman=bool(isHuman))
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = VideoSquareTemplateSerializer(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        elif size == "9:16":
            if _query:
                queryset = VideoTemplate.objects.filter(vVideo__isnull=False,name__icontains =_query)
            else:
                queryset = VideoTemplate.objects.filter(vVideo__isnull=False)
            if isHuman!=None:
                queryset = queryset.filter(isHuman=bool(isHuman))
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = VideoVerticalTemplateSerializer(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            if _query:
                queryset = VideoTemplate.objects.filter(hVideo__isnull=False,name__icontains =_query)
            else:
                queryset = VideoTemplate.objects.filter(hVideo__isnull=False)
            if isHuman!=None:
                queryset = queryset.filter(isHuman=bool(isHuman))
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = VideoHorizontalTemplateSerializer(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)


class FontsView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FontFamilySerializer
    
    def get(self, request, format=None):
        _fontQuery = FontFamily.objects.all()
        content = {'results': self.serializer_class(_fontQuery,many=True,context={'request': request}).data}
        return Response(content,status=status.HTTP_200_OK)



class DownloadVideoGenerateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainVideoGenerateWithMergeTagSerializer

    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            queryset = MainVideoGenerate.objects.filter(videoCreator=inst,generationType=1).order_by('-timestamp')
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if inst.mainVideoGenerate:
                _reqMTag = json.loads(inst.mergeTag)
                _mergeTagData = request.data.get("mergeTagData",{})
                _mergeTagValue = []
                _errorTag = {}
                isError = False
                if len(_reqMTag)>0:
                    if not _mergeTagData:
                        content = {'mergeTagData': ['This field is Required.'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                    try:
                        # validate merge Tag
                        for _mt in _reqMTag:
                            _tag,_type = _mt
                            _mtagValue = _mergeTagData.get(_tag,None)
                            _isValid,message = validateMtag(_mt,_mtagValue)
                            if _isValid:
                                _mergeTagValue.append(_mtagValue)
                            else:
                                _errorTag[_tag] = message
                                isError = True
                        if isError:
                            content = {'mergeTagData': _errorTag,'message': 'Some Value of Merge Tag is not Correct.','isError': True}
                            return Response(content,status=status.HTTP_200_OK)
                        ## create mainVideoGenerate
                        _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst,mergeTagValue=json.dumps(_mergeTagValue),allMergeTag=inst.allMergeTag,generationType=1)
                        # set thumbnail based on parent
                        if ct:
                            _gInst.generateVideo()
                        # else video is in progress
                        serializer = self.serializer_class(_gInst,context={'request': request})
                        content = {'result': serializer.data,'isError': False}
                        commandData = {'id': inst.id,'results': serializer.data,'type': 'download_history'}
                        fire.eventFire(inst.user,"videoEditor.progress.add",commandData)

                        # update credit
                        _meta = {"type": "PERSONALIZE_VIDEO","generationType": 1,"usedCredit": 1,"id": f"{_gInst.id}","videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","userId": f"{_gInst.videoCreator.user.id}"}
                        newVideoCreatorTask.addCreditTask.delay(_meta)

                        return Response(content,status=status.HTTP_200_OK)

                    except Exception as e:
                        content = {'mergeTagData': [f'This field is not Valid.\n{e} {str(traceback.format_exc())}'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                else:
                    # already generated
                    _videoGenerate = inst.mainVideoGenerate
                    serializer = self.serializer_class(_videoGenerate,context={'request': request})
                    content = {'result': serializer.data,'isError': False}
                    return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Main Video is not Generated.'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

class SoloVideoGenerateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainVideoGenerateCampaignSerializer

    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            queryset = MainVideoGenerate.objects.filter(videoCreator=inst,generationType=2).order_by('-timestamp')
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if inst.mainVideoGenerate:
                _reqMTag = json.loads(inst.allMergeTag)
                _mergeTagData = request.data.get("mergeTagData",{})
                _mergeTagValue = []
                _errorTag = {}
                isError = False
                if len(_reqMTag)>0:
                    if not _mergeTagData:
                        content = {'mergeTagData': ['This field is Required.'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                    try:
                        # validate merge Tag
                        for _mt in _reqMTag:
                            _tag,_type = _mt
                            _mtagValue = _mergeTagData.get(_tag,None)
                            _isValid,message = validateMtag(_mt,_mtagValue)
                            if _isValid:
                                _mergeTagValue.append(_mtagValue)
                            else:
                                _errorTag[_tag] = message
                                isError = True
                        if isError:
                            content = {'mergeTagData': _errorTag,'message': 'Some Value of Merge Tag is not Correct.','isError': True}
                            return Response(content,status=status.HTTP_200_OK)
                        ## create mainVideoGenerate
                        
                        # personalise salespage
                        _personlizeData = {"page": {'isP': inst.sharingPage.isPersonalized,'name': inst.sharingPage.name,'id': f"{inst.sharingPage.id}"}}
                        # personlize thumbnail
                        _personlizeData["thumbnail"] = {'isP': inst.thumbnailInst.isPersonalized,'name': inst.thumbnailInst.name,'id': f"{inst.thumbnailInst.id}"}

                        #add sharing PageData
                        finst = salesPageSerilaizers.SalesPageEditorSerializer(inst.sharingPage,context={'request': request}).data
                        mergeVData = []
                        for n,_mt in enumerate(_reqMTag):
                            _tag,_type = _mt
                            if _type =='text':
                                _mtagValue =_mergeTagValue[n]
                                mergeVData.append([_tag,_mtagValue])

                        for ind,ii in enumerate(finst['textEditor']):
                            text = ii['content']
                            for ii in mergeVData:
                                text = text.replace(ii[0],ii[1])
                            finst['textEditor'][ind]['content'] = text
                        _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst,mergeTagValue=json.dumps(_mergeTagValue),allMergeTag=inst.allMergeTag,generationType=2,sharingPageData = json.dumps(finst))
                        # set thumbnail based on parent
                        if ct:
                            _gInst.generateVideo()
                        # else video is in progress
                        serializer = self.serializer_class(_gInst,context={'request': request})
                        content = {'result': serializer.data,'isError': False}
                        commandData = {'id': inst.id,'results': serializer.data,'type': 'solo_history'}
                        fire.eventFire(inst.user,"videoEditor.progress.add",commandData)

                        # update credit
                        if len(json.loads(inst.mergeTag)):
                            _meta = {"type": "PERSONALIZE_VIDEO","generationType": _gInst.generationType,"usedCredit": 1,"id": f"{_gInst.id}","videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","userId": f"{_gInst.videoCreator.user.id}"}
                            newVideoCreatorTask.addCreditTask.delay(_meta)
                        if _personlizeData["page"]["isP"]:
                            _meta = {"type": "PERSONALIZE_PAGE","generationType": _gInst.generationType,"usedCredit": 1,"id": _personlizeData["page"]["id"],"videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","pageName": _personlizeData["page"]["name"],"userId": f"{_gInst.videoCreator.user.id}"}
                            newVideoCreatorTask.addCreditTask.delay(_meta)
                        if _personlizeData["thumbnail"]["isP"]:
                            _meta = {"type": "PERSONALIZE_THUMBNAIL","generationType": _gInst.generationType,"usedCredit": 1,"id": _personlizeData["thumbnail"]["id"],"videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","thumbnailName": _personlizeData["thumbnail"]["name"],"userId": f"{_gInst.videoCreator.user.id}"}
                            newVideoCreatorTask.addCreditTask.delay(_meta)

                        return Response(content,status=status.HTTP_200_OK)

                    except Exception as e:
                        content = {'mergeTagData': [f'This field is not Valid.\n{e} {str(traceback.format_exc())}'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                else:
                    # already generated
                    _videoGenerate = inst.mainVideoGenerate
                    serializer = self.serializer_class(_videoGenerate,context={'request': request})
                    content = {'result': serializer.data,'isError': False}
                    return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Main Video is not Generated.'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class SoloMailVideoGenerateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainVideoGenerateSoloMailSerializer

    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            queryset = MainVideoGenerate.objects.filter(videoCreator=inst,generationType=4).order_by('-timestamp')
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if inst.mainVideoGenerate:
                _reqMTag = json.loads(inst.allMergeTag)
                _mergeTagData = request.data.get("mergeTagData",{})
                _mergeTagValue = []
                _errorTag = {}
                isError = False
                if len(_reqMTag)>0:
                    if not _mergeTagData:
                        content = {'mergeTagData': ['This field is Required.'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                    try:
                        # validate merge Tag
                        for _mt in _reqMTag:
                            _tag,_type = _mt
                            _mtagValue = _mergeTagData.get(_tag,None)
                            _isValid,message = validateMtag(_mt,_mtagValue)
                            if _isValid:
                                _mergeTagValue.append(_mtagValue)
                            else:
                                _errorTag[_tag] = message
                                isError = True
                        if isError:
                            content = {'mergeTagData': _errorTag,'message': 'Some Value of Merge Tag is not Correct.','isError': True}
                            return Response(content,status=status.HTTP_200_OK)
                        ## create mainVideoGenerate

                        # personalise salespage
                        _personlizeData = {"page": {'isP': inst.sharingPage.isPersonalized,'name': inst.sharingPage.name,'id': f"{inst.sharingPage.id}"}}
                        # personlize thumbnail
                        _personlizeData["thumbnail"] = {'isP': inst.thumbnailInst.isPersonalized,'name': inst.thumbnailInst.name,'id': f"{inst.thumbnailInst.id}"}

                        
                        #add sharing PageData
                        finst = salesPageSerilaizers.SalesPageEditorSerializer(inst.sharingPage,context={'request': request}).data
                        mergeVData = []
                        for n,_mt in enumerate(_reqMTag):
                            _tag,_type = _mt
                            if _type == 'text':
                                _mtagValue =_mergeTagValue[n]
                                mergeVData.append([_tag,_mtagValue])

                        for ind,ii in enumerate(finst['textEditor']):
                            text = ii['content']
                            for ii in mergeVData:
                                text = text.replace(ii[0],ii[1])
                            finst['textEditor'][ind]['content'] = text
                        _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst,mergeTagValue=json.dumps(_mergeTagValue),allMergeTag=inst.allMergeTag,generationType=4,sharingPageData = json.dumps(finst))
                        # set thumbnail based on parent
                        if ct:
                            _gInst.generateVideo()
                        
                        serializer = self.serializer_class(_gInst,context={'request': request})
                        content = {'result': serializer.data,'isError': False}
                        commandData = {'id': inst.id,'results': serializer.data,'type': 'solomail_history'}
                        fire.eventFire(inst.user,"videoEditor.progress.add",commandData)

                        # update credit
                        if len(json.loads(inst.mergeTag)):
                            _meta = {"type": "PERSONALIZE_VIDEO","generationType": _gInst.generationType,"usedCredit": 1,"id": f"{_gInst.id}","videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","userId": f"{_gInst.videoCreator.user.id}"}
                            newVideoCreatorTask.addCreditTask.delay(_meta)
                        if _personlizeData["page"]["isP"]:
                            _meta = {"type": "PERSONALIZE_PAGE","generationType": _gInst.generationType,"usedCredit": 1,"id": _personlizeData["page"]["id"],"videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","pageName": _personlizeData["page"]["name"],"userId": f"{_gInst.videoCreator.user.id}"}
                            newVideoCreatorTask.addCreditTask.delay(_meta)
                        if _personlizeData["thumbnail"]["isP"]:
                            _meta = {"type": "PERSONALIZE_THUMBNAIL","generationType": _gInst.generationType,"usedCredit": 1,"id": _personlizeData["thumbnail"]["id"],"videoId": f"{_gInst.videoCreator.id}","name": f"{_gInst.videoCreator.name}","thumbnailName": _personlizeData["thumbnail"]["name"],"userId": f"{_gInst.videoCreator.user.id}"}
                            newVideoCreatorTask.addCreditTask.delay(_meta)

                        return Response(content,status=status.HTTP_200_OK)

                    except Exception as e:
                        content = {'mergeTagData': [f'This field is not Valid.\n{e} {str(traceback.format_exc())}'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                else:
                    # already generated
                    _videoGenerate = inst.mainVideoGenerate
                    serializer = self.serializer_class(_videoGenerate,context={'request': request})
                    content = {'result': serializer.data,'isError': False}
                    return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Main Video is not Generated.'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


import pandas as pd

class CSVValidaterView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    bypassEmailValidation = True

    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)

    def post(self,request,pk,format=None):
        user = request.user
        data = request.data
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            # if (user.totalVideoCredit - user.usedVideoCredit)<=0:
            #     content = {'detail': 'Not Enough Video Credit'}
            #     return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            # if user.subs_end:
            #     if timezone.now()>user.subs_end:
            #         content = {"error2": { 1: { "message" :"Subscription Ended."}}}
            #         return Response(content,status=status.HTTP_200_OK)
            #         # content = {'detail': 'Subscriptions End'}
            #         # return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            # else:
            #     content = {"error2": { 1: { "message" :"Subscription Ended."}}}
            #     return Response(content,status=status.HTTP_200_OK)

            mergeTagMap = data.get('mergeTagMap',None)
            if not mergeTagMap:
                content = {"mergeTagMap": ["This Field is Required."],"isError": True}
                return Response(content,status=status.HTTP_200_OK)

            allMergeTag = [["{{email}}","email"]] + json.loads(inst.allMergeTag)
            #allMergeTag.append(["{{email}}","email"])
            csvFileId = data.get('csvFile',None)

            totalContacts = 0
            if not csvFileId:
                content = {"csvFile": ["This Field is Required."],"isError": True}
                return Response(content,status=status.HTTP_200_OK)
            try:
                csvFileInst = FileUpload.objects.get(user=user,id=csvFileId)
            except:
                content = {"csvFile": ["file doesn't exist."],"isError": True}
                return Response(content,status=status.HTTP_200_OK)
        
            try:
                allData = pd.read_csv(csvFileInst.media_file.path, engine='python')
                allData = allData.fillna("")
                totalContacts = allData.shape[0]
                if totalContacts==0:
                    content = {"csvFile": ["No Data Found Inside CSV."],"isError": True}
                    return Response(content,status=status.HTTP_200_OK)
                allColumns = allData.columns.tolist()
            except:
                content = {"csvFile": ["File is not valid."],"isError": True}
                return Response(content,status=status.HTTP_200_OK)

            fData = {}
            _fData = {}
            _allValidTag = []
            reqMT = {}

            for _tag in allMergeTag:
                
                try:
                    _cln = mergeTagMap.get(f"{_tag[0]}_{_tag[1]}",None)
                    if _cln:
                        if _cln not in allColumns:
                            reqMT[f"{_tag[0]}_{_tag[1]}"]= ['Map Column Name ({_cln}) not found in CSV.']
                        else:
                            fData[f"{_tag[0]}_{_tag[1]}"] = _cln
                            _fData[f"{_tag[0]}_{_tag[1]}"] = _tag
                            _allValidTag.append(_cln)
                    else:
                        reqMT[f"{_tag[0]}_{_tag[1]}"]= ['This field is not Valid.']
                except:
                    reqMT[f"{_tag[0]}_{_tag[1]}"]= ['This field is Required.']
                
            if len(reqMT)!=0:
                content = {"mergeTagMap": reqMT,"isError": True}
                return Response(content,status=status.HTTP_200_OK)

            # validate csv each column
            allReadyAddedOne = MainVideoGenerate.objects.filter(videoCreator=inst).values_list('uniqueIdentity', flat=True)
            

            #validate csv
            alreadyAddedUniqueIdentifier = {uid: True for uid in allReadyAddedOne}
            finalData = []
            errors1 = {}

            finalErrorCount = 0
            allCExcelIndex = {}
            for ii in fData:
                allCExcelIndex[ii] = chr(65+allColumns.index(fData[ii]))

            for index, row in allData.iterrows():
                currentData = {}
                totalErrorCount = 0
                #columnIndex = chr(65+allColumns.index())
                errors1[index+1] = []
                errors1[index+1] = {"email": "","data": []}


                for nn,ii in enumerate(fData):
                    curntMData = row[fData[ii]]
                    if self.bypassEmailValidation and ii == "{{email}}_email":
                        _isValid,message = validateMtag([_fData[ii][0],"text"],curntMData,True)
                    else:
                        _isValid,message = validateMtag(_fData[ii],curntMData,True)
                    if not _isValid:
                        errors1[index+1]['data'].append({"message": message,"cellIndex": f"{allCExcelIndex[ii]}{index+1}"})
                        totalErrorCount+=1
                    else:
                        ## handle unique identifier
                        if ii == "{{email}}_email":
                            # validate uniqueness
                            errors1[index+1]['email'] = curntMData
                            if alreadyAddedUniqueIdentifier.get(curntMData.lower(),None):
                                ## already exist uniqeness
                                errors1[index+1]['data'].append({"message": f"{_fData[ii][0]} should be unique.","cellIndex": f"{allCExcelIndex[ii]}{index+1}"})
                                totalErrorCount+=1
                            else:
                                currentData[ii] = curntMData
                                alreadyAddedUniqueIdentifier[curntMData.lower()] = True
                        else:
                            currentData[ii] = curntMData
                    
                if totalErrorCount==0:
                    finalData.append(currentData)
                finalErrorCount+=totalErrorCount

                if len(errors1[index+1]["data"])==0:
                    errors1.pop(index+1)

            
            #save csv
            _crnFileName = f"{uuid4()}.csv"
            df = pd.DataFrame(finalData)
            stinst = GroupHandler(videoCreator=inst,fileName=csvFileInst.name,mergeTagMap=json.dumps(fData),allMergeTag=json.dumps(allMergeTag),mailClient=inst.mailClient.id,isValidated=True,totalCount=len(allData))
            
            stinst.csvFile.name = stinst.getCsvName(_crnFileName)
            stinst.originalFile.name = stinst.getOriginalName(_crnFileName)
            stinst.save()
            

            df.to_csv(stinst.getCsvPath(_crnFileName),index=False)
            copy(csvFileInst.media_file.path,stinst.getOriginalPath(_crnFileName))
            isError = False
            if finalErrorCount>0:
                isError = True
            content = {'id': str(stinst.id),'isError': isError,'totalSkipped': len(errors1),'totalErrors':  finalErrorCount, 'errors': errors1,'totalContacts': totalContacts}
            return Response(content,status=status.HTTP_200_OK)

        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


def addCsvDataToDb(inst,_parseCsv,allReqMtag,onlyTextMTag,_salesPageData,_personlizeData):
    totalAdded = 0
    for index, row in _parseCsv.iterrows():
        try:
            finalTagValue = [row[ii] for ii in allReqMtag]
            _finalTagValueDict = {ii: row[ii] for ii in allReqMtag}
            #add sharing PageData
            mergeVData = []
            for _mt in onlyTextMTag:
                mergeVData.append([_mt,_finalTagValueDict[f"{_mt}_text"]])

            finst = json.loads(_salesPageData)
            for ind,ii in enumerate(finst['textEditor']):
                text = ii['content']
                for ii in mergeVData:
                    text = text.replace(ii[0],ii[1])
                finst['textEditor'][ind]['content'] = text

            _gInst,ct = MainVideoGenerate.objects.get_or_create(videoCreator=inst.videoCreator,mergeTagValue=json.dumps(finalTagValue),allMergeTag=inst.allMergeTag,generationType=3,sharingPageData = json.dumps(finst),groupHandlerTracker=inst,uniqueIdentity=_finalTagValueDict["{{email}}_email"])
            # set thumbnail based on parent
            if ct:
                _gInst.generateVideo()
            totalAdded += 1
        except:
            pass
    inst.isAdded = True
    inst.totalCount = totalAdded
    inst.save()

    # update credit
    if len(json.loads(inst.videoCreator.mergeTag)):
        _meta = {"type": "PERSONALIZE_VIDEO","generationType": 3,"usedCredit": totalAdded,"id": f"{inst.id}","videoId": f"{inst.videoCreator.id}","name": f"{inst.videoCreator.name}","csvName": inst.fileName,"userId": f"{inst.videoCreator.user.id}"}
        newVideoCreatorTask.addCreditTask.delay(_meta)
    if _personlizeData["page"]["isP"]:
        _meta = {"type": "PERSONALIZE_PAGE","generationType": 3,"usedCredit": totalAdded,"id": _personlizeData["page"]["id"],"videoId": f"{inst.videoCreator.id}","name": f"{inst.videoCreator.name}","pageName": _personlizeData["page"]["name"],"userId": f"{inst.videoCreator.user.id}"}
        newVideoCreatorTask.addCreditTask.delay(_meta)
    if _personlizeData["thumbnail"]["isP"]:
        _meta = {"type": "PERSONALIZE_THUMBNAIL","generationType": 3,"usedCredit": totalAdded,"id": _personlizeData["thumbnail"]["id"],"videoId": f"{inst.videoCreator.id}","name": f"{inst.videoCreator.name}","thumbnailName": _personlizeData["thumbnail"]["name"],"userId": f"{inst.videoCreator.user.id}"}
        newVideoCreatorTask.addCreditTask.delay(_meta)





class EmailGenerateHistoryView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailGenerateHistorySerializer
        
    def get_object(self, pk,request):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except TempVideoCreator.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        _type = convertInt(request.GET.get('type',None),None)
        if is_exist:
            if _type==None:
                queryset = EmailGenTracker.objects.filter(videoCreator=inst).order_by('-timestamp')
            else:
                queryset = EmailGenTracker.objects.filter(videoCreator=inst,_type=_type).order_by('-timestamp')

            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class EmailCSVHistoryDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailGenerateHistorySerializer
        
    def get_object(self, pk,request):
        try:
            _inst = GroupHandler.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.videoCreator.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except GroupHandler.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            queryset = MainVideoGenerate.objects.filter(groupHandlerTracker=inst)
            if queryset.count():
                _firstInst = queryset.first()
                headers = json.loads(_firstInst.allMergeTag)
                headers += [["status","text"],["campaignUrl","text"]]
                results = self.paginate_queryset(queryset, request, view=self)
                finalData = []
                for _inst in results:
                    _rawData = json.loads(_inst.mergeTagValue)
                    _crntSharingPageUrl = f"https://autovid.ai/p/{_inst.videoCreator.slug}/{_inst.uniqueIdentity}"
                    # if _inst._shortUrl:
                    #     _crntSharingPageUrl = _inst._shortUrl.getUrl()
                    # else:
                    #     _crntSharingPageUrl = f"https://autovid.ai/p/{_inst.videoCreator.slug}/{_inst.uniqueIdentity}"
                    _rawData += [_inst.status,_crntSharingPageUrl]
                    finalData.append(_rawData)
                #serializer = self.serializer_class(results, many=True,context={'request': request})
                return self.get_paginated_response({"data": finalData,"headers": headers})
            else:
                content = {"data": [],"headers": [["{{email}}","email"],["status","text"],["campaignUrl","text"]]}
                return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class GenerateCSVValidaterView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = BatchMailMinSerializer

    def get_object(self, pk,request):
        try:
            _inst = GroupHandler.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if _inst.videoCreator.user.id == user.id:
                return (True,_inst)
            return (False,None)
        except:
            return (False,None)

    def get(self,request,pk,format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _parseCsv = pd.read_csv(inst.csvFile.path, engine='python')
            allMergeTag = json.loads(inst.allMergeTag)
            allReqMtag = [f"{i[0]}_{i[1]}" for i in allMergeTag]
            onlyTextMTag = [i[0] for i in allMergeTag if i[1]=='text']

            # personalise salespage
            _personlizeData = {"page": {'isP': inst.videoCreator.sharingPage.isPersonalized,'name': inst.videoCreator.sharingPage.name,'id': f"{inst.videoCreator.sharingPage.id}"}}
            # personlize thumbnail
            _personlizeData["thumbnail"] = {'isP': inst.videoCreator.thumbnailInst.isPersonalized,'name': inst.videoCreator.thumbnailInst.name,'id': f"{inst.videoCreator.thumbnailInst.id}"}

            _salesPageData = salesPageSerilaizers.SalesPageEditorSerializer(inst.videoCreator.sharingPage,context={'request': request}).data
            inst.sharingPageData = json.dumps(_salesPageData)
            inst.thumbnailInst = inst.videoCreator.thumbnailInst
            inst.addShortUrl()
            inst.save()
            
            _inst,ct = EmailGenTracker.objects.get_or_create(videoCreator=inst.videoCreator,_type=1,groupInst=inst)

            _th = Thread(target=addCsvDataToDb,args=(inst,_parseCsv,allReqMtag,onlyTextMTag,inst.sharingPageData,_personlizeData,))
            _th.start()
            serializer = self.serializer_class(inst,context={'request': request})
            content = {'result': serializer.data,'isError': False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self,request,pk,format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if not (inst.isAdded or inst.status==3):
                inst.delete()
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)




class BatchGeneratedHistoryFileView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = BatchGeneratedHistoryFileSerializer
        
    def get_object(self, pk,request):
        try:
            _inst = GroupHandler.objects.get(id=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.videoCreator.user.id or _token == settings.SERVER_TOKEN:
                return (True,_inst)
            return (False,None)
        except GroupHandler.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if inst.status!=1 or (not inst.generatedFile):
                # regenerate file
                inst.generateCSVFile()
            serializer = self.serializer_class(inst,context={'request': request})
            content = {'result': serializer.data,'isError': False}
            commandData = {'id': inst.videoCreator.id,'results': serializer.data,'type': 'batch_history'}
            fire.eventFire(inst.videoCreator.user,"videoEditor.progress.add",commandData)
            return Response(content,status=status.HTTP_200_OK)

        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)




class RealTimeNonAvatarMTagView(APIView):
    permission_classes = (AllowAny,)
   
    def get_object(self, pk):
        try:
            _inst = MainVideoGenerate.objects.get(id=pk)
            return (True,_inst)
        except MainVideoGenerate.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk)
        if is_exist:
            result = {"name": inst.videoCreator.name,"mainVideo": inst.video.url}
            if inst.videoCreator.objTagData and inst.videoCreator.type == 2:
                result["objectsData"] = json.loads(inst.videoCreator.objTagData)

                _jsonData = json.loads(inst.videoCreator.jsonData)
                for _sceneIndex in result["objectsData"]:
                    try:
                        _sceneData = _jsonData[_sceneIndex]["jsonData"]["objects"]
                        _sceneObjMap = {obj["id"]: n for n,obj in enumerate(_sceneData)}

                        jsonObj = []
                        for _obj in result["objectsData"][_sceneIndex]["sceneInfo"]["objects"]:
                            jsonObj.append(_sceneData[_sceneObjMap[_obj["id"]]])
                        result["objectsData"][_sceneIndex]["fabObjects"] = jsonObj
                    except:
                        pass
                    
            content = {'result': result}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)