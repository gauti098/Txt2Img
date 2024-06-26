from shutil import copy
from uuid import uuid4
from django.conf import settings
from rest_framework import status

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
import json,traceback
import logging
from django.utils import timezone
from threading import Thread
from newVideoCreator.utils.validateMergeTag import validateMtag
from utils.common import convertInt

from events import fire


logger = logging.getLogger(__name__)

from newVideoCreator.models import (
    TempVideoCreator,setDefaultThumbnail
)

from newImageEditor.models import (
    ImageCreator,
    ImageCreatorGenerated,
    IMAGECREATORGENERATED_UUID_TOTAL_NO
)
from newImageEditor.serializers import (
    ImageCreatorDetailSerializer,
    ImageCreatorMinSerializer,
    ImageCreatorSerializer,
    ImageCreatorDetailsSerializer,
    ImageCreatorSoloLinkSerializer
)

class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50

class ImageCreatorCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ImageCreatorMinSerializer

    def post(self, request, format=None):
        user = request.user
        _jsonData = request.data.get("d","")
        _name = request.data.get("name","")
        try:
            _jsonData = json.dumps(json.loads(_jsonData))
            _inst = ImageCreator(user=user,jsonData=_jsonData)
            if _name:
                _inst.name = _name
            _inst.save()
            _inst.updateThumbnail()
            content = {"result": self.serializer_class(_inst,context={'request': request}).data}
            return Response(content,status=status.HTTP_200_OK)
        except Exception as e:
            content = {"message": "Data is not Valid"}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)


class ImageCreatorView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = ImageCreatorSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order',None)
        filter = data.get('q','')

        _isGenerated = bool(convertInt(data.get('generated',1),1))

        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp',6: '-generatedAt',7: '-generatedAt'}
        isOrder = None
        queryset = ImageCreator.objects.filter(user=request.user,isDeleted=False,isAutoGenerated=False,isGenerated=_isGenerated)
        if _isGenerated:
            queryset = queryset.order_by('-generatedAt')
        else:
            queryset = queryset.order_by('-updated')

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


class ImageTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = ImageCreatorSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','0')
        filter = data.get('q','')
        

        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        queryset = ImageCreator.objects.filter(isTemplate=1,isDeleted=False)
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


class CopyImageCreatorView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,request):
        try:
            _inst = ImageCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if (user.id == _inst.user.id or _inst.isTemplate==1) and _inst.isDeleted==False:
                return (True,_inst)
            return (False,None)
        except ImageCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):

        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _new = ImageCreator(user=request.user,name=f"Copy of {inst.name}",jsonData=inst.jsonData)
            _filename = f"{uuid4()}.jpeg"
            _new.thumbnail.name = _new.getThumbnailName(_filename)
            copy(inst.thumbnail.path,_new.getThumbnailPath(_filename))
            _new.save()
            content = {'result': {'id': _new.id}}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class CopyVideoCreatorView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request,pk, format=None):
        _sceneIndex = convertInt(request.GET.get("sceneIndex",0))
        is_exist,inst = TempVideoCreator.isValidUser(request.user,pk)
        if is_exist:
            _isJ,jsonData = inst.getOnlyOneSceneJsonData(_sceneIndex)
            if _isJ:
                _new = ImageCreator(user=request.user,name=f"Copy of {inst.name}",jsonData=jsonData)
                _new.save()
                _new.updateThumbnail()
                content = {'result': {'id': _new.id}}
                return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': jsonData}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


def updateThumbnailOnSave(_id):
    try:
        _inst = ImageCreator.objects.get(id=_id)
        _updatedDiff = timezone.now() - _inst.updated
        if _updatedDiff.seconds>20:
            _inst.updateThumbnail()
    except Exception as e:
        logger.error(f"Unable To Update Draft Thumbnail: {e} {str(traceback.format_exc())}" )



class ImageCreatorUpdateView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ImageCreatorDetailsSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = ImageCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id and _inst.isDeleted==False:
                return (True,_inst)
            elif _inst.isTemplate==1 and _inst.isDeleted==False:
                return (2,_inst)
            elif _token == settings.SERVER_TOKEN:
                return (3,_inst)
            return (False,None)
        except ImageCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _result = self.serializer_class(inst,context={'request': request}).data
            _videoId = request.GET.get('videoId',None)
            if is_exist==3:
                try:
                    _videoInst = TempVideoCreator.objects.get(id=_videoId)
                    if _videoInst.parseData:
                        _avatarInfo = json.loads(_videoInst.parseData)["avatarInfo"]
                        if _avatarInfo["isImageId"]:
                            _avatarId = _avatarInfo["imageId"]
                            _result["jsonData"] = json.dumps(inst.replaceAvatar(_avatarId))
                except:
                    pass
            content = {'result': _result}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist==True:
            if inst.isTemplate==1:
                return Response({'detail': "Template Cannot Update."},status=status.HTTP_200_OK)
            if inst.isGenerated:
                return Response({'detail': "Cannot Update after generated."},status=status.HTTP_200_OK)
            _jsonData = request.data.get("d",None)
            _name = request.data.get("name","")
            if _name:
                inst.name = _name
            if _jsonData:
                inst.jsonData = _jsonData
            inst.save()
            inst.updateThumbnail()
            return Response("OK",status=status.HTTP_200_OK)
        else:
            content = {'message': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        
    def put(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist==True:
            if inst.isTemplate==1:
                return Response({'detail': "Template Cannot Update."},status=status.HTTP_200_OK)
            if inst.isGenerated:
                return Response({'detail': "Cannot Update after generated."},status=status.HTTP_200_OK)
            _jsonData = request.data.get("d",None)
            _name = request.data.get("name","")
            _isGenerated = request.data.get("isGenerated",None)
            if _isGenerated:
                inst.onGenerate()
                commandData =  ImageCreatorSerializer(inst,context={'request': request}).data
                fire.eventFire(inst.user,"imageEditor.add",commandData)
                return Response(True,status=status.HTTP_200_OK)

            if _name:
                inst.name = _name
                inst.save()
            if _jsonData:
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
        if is_exist==True:
            if inst.isTemplate==1:
                return Response({'detail': "Template Cannot Deleted."},status=status.HTTP_200_OK)
            if inst.isAutoGenerated:
                return Response({'detail': "Cannot Deleted Default Scene Thumbnail."},status=status.HTTP_200_OK)
            name = inst.name
            commandData = {"id": inst.id}
            fire.eventFire(inst.user,"imageEditor.remove",commandData)
            if inst.isGenerated:
                inst.isDeleted = True
                inst.save()
                # update to default
                _th = Thread(target=setDefaultThumbnail,args=(inst,request,))
                _th.start()
            else:
                inst.delete()
            content = {'name': name,'isError': False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

from campaign import models as campaignModels
class ImageCreatorDetailsView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ImageCreatorDetailSerializer
    
    def get_object(self, pk,request):
        try:
            _inst = ImageCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id and _inst.isDeleted==False:
                return (True,_inst)
            elif _inst.isTemplate==1 and _inst.isDeleted==False:
                return (2,_inst)
            elif _token == settings.SERVER_TOKEN:
                return (3,_inst)
            return (False,None)
        except ImageCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _result = self.serializer_class(inst,context={'request': request}).data
            content = {'result': _result}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _data = request.data
            # update mail client
            isUpdate=False
            _mailClient = _data.get('mailClient',None)
            
            if _mailClient:
                try:
                    _mailClientInst = campaignModels.EmailClient.objects.get(id=_mailClient)
                    inst.mailClient = _mailClientInst
                    isUpdate = True
                except:
                    content = {"mailClient": ['This Field is not Valid.'],"isError": True}
                    return Response(content,status=status.HTTP_200_OK)

            _name = _data.get('name',None)
            if _name:
                inst.name = _name
                isUpdate = True

            _redirectUrl = _data.get('redirectUrl',None)
            if _redirectUrl!=None:
                inst.redirectUrl = _redirectUrl
                isUpdate = 2

            content = {"isError": False}
            if isUpdate:
                inst.save()
                if isUpdate == 2:
                    _result = self.serializer_class(inst,context={'request': request}).data
                    content["result"] = {"code": _result["code"]}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


    def delete(self,request,pk):
        is_exist,inst = self.get_object(pk,request)
        if is_exist==True:
            if inst.isTemplate==1:
                return Response({'detail': "Template Cannot Deleted."},status=status.HTTP_200_OK)
            if inst.isAutoGenerated:
                return Response({'detail': "Cannot Deleted Default Scene Thumbnail."},status=status.HTTP_200_OK)
            name = inst.name
            commandData = {"id": inst.id}
            fire.eventFire(inst.user,"imageEditor.remove",commandData)
            if inst.isGenerated:
                inst.isDeleted = True
                inst.save()
                # update to default
                _th = Thread(target=setDefaultThumbnail,args=(inst,request,))
                _th.start()
            else:
                inst.delete()
            content = {'name': name,'isError': False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class GenerateImageView(APIView):
    permission_classes = (AllowAny,)
    
    def get_object(self, pk,request):
        try:
            _inst = ImageCreator.objects.get(pk=pk)
            _token = request.GET.get('token',None)
            user = request.user
            if user.id == _inst.user.id and _inst.isDeleted==False:
                return (True,_inst)
            elif _inst.isTemplate==1 and _inst.isDeleted==False:
                return (2,_inst)
            elif _token == settings.SERVER_TOKEN:
                return (2,_inst)
            return (False,None)
        except ImageCreator.DoesNotExist:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if not inst.isGenerated:
                inst.onGenerate()
                commandData =  ImageCreatorSerializer(inst,context={'request': request}).data
                fire.eventFire(inst.user,"imageEditor.add",commandData)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': True}
            return Response(content,status=status.HTTP_200_OK)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _name = request.data.get("name",None)
            if _name:
                inst.name = _name
                inst.save()
                
            if not inst.isGenerated:
                inst.onGenerate()
                commandData =  ImageCreatorSerializer(inst,context={'request': request}).data
                fire.eventFire(inst.user,"imageEditor.add",commandData)
            return Response(True,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': True}
            return Response(content,status=status.HTTP_200_OK)


    def put(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            _mergeTag = inst.getMergeTag()
            if _mergeTag:
                inst.isPersonalized = True
                inst.mergeTag = json.dumps(_mergeTag)
                inst.save()

            _tagV = request.data.get("tagValue",[])
            if _tagV:
                inst.updateThumbnailWithMTag(_tagV)
            commandData =  ImageCreatorSerializer(inst,context={'request': request}).data
            commandData["mergeTag"] = _mergeTag
            return Response(commandData,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': True}
            return Response(content,status=status.HTTP_200_OK)


from django.http import FileResponse
import os,re
from urllib.parse import unquote

class GenerateImageThumbnailView(APIView):
    permission_classes = (AllowAny,)

    def get_object(self, uid):
        try:
            inst = ImageCreator.objects.get(_uid = uid)
            return (True,inst)
        except:
            return (False,None)

    def get(self, request, format=None):
        data = request.GET
        uid = data.get('uid','')
        is_exist,inst= self.get_object(uid)
        if is_exist:
            _fullP = request.get_full_path()
            _fullP = '?'.join(_fullP.split('?')[1:])
            _rawGet = unquote(_fullP)
            _parseMTag = {}
            _reg = r'({{.*?\}})_(text|url|email)=((?:(?!&{{).)*)'
            for _t in re.findall(_reg,_rawGet):
                _parseMTag[f"{_t[0]}_{_t[1]}"] = _t[2]

            thumbnailPath = inst.generateImageWithMTagRealtime(_parseMTag)[0]
            
            isFound = os.path.isfile(thumbnailPath)
            if isFound:
                img = open(thumbnailPath,'rb')
                return FileResponse(img) 

        # if thumbnail not exist return default
        _thumbnailPath = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'404_with_reload.jpg')
        return FileResponse(open(_thumbnailPath,'rb'))



class SaveTempleteView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, uid):
        try:
            inst = ImageCreator.objects.get(id = uid)
            if inst.isTemplate==1 and inst.isDeleted==False:
                return (True,inst)
            return (False,None)
        except:
            return (False,None)

    def get(self, request,pk, format=None):
        is_exist,inst= self.get_object(pk)
        if is_exist:
            _inst = ImageCreator(user=request.user,name=inst.name,jsonData=inst.jsonData,mergeTag=inst.mergeTag,isPersonalized=inst.isPersonalized,isGenerated=True,ratio=inst.ratio,_videoId=inst._videoId)
            _inst.save()
            _inst.thumbnail.name = inst.thumbnail.name
            _inst.save()
            return Response({'result': {'id': _inst.id}},status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': True}
            return Response(content,status=status.HTTP_200_OK)



class GenerateImageLinkView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = ImageCreatorSoloLinkSerializer

    def get_object(self, pk,request):
        try:
            _inst = ImageCreator.objects.get(user=request.user,pk=pk,isDeleted=False)
            return (True,_inst)
        except ImageCreator.DoesNotExist:
            return (False,None)
    
    def get(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            queryset = ImageCreatorGenerated.objects.filter(imageCreator=inst,generationType=1).order_by('-timestamp')
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        is_exist,inst = self.get_object(pk,request)
        if is_exist:
            if inst.isGenerated:
                _reqMTag = json.loads(inst.mergeTag)
                _mergeTagData = request.data.get("mergeTagData",{})
                _parseMTag = {}
                _errorTag = {}
                isError = False
                if len(_reqMTag)>0:
                    if not _mergeTagData:
                        content = {'mergeTagData': ['This field is Required.'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                    try:
                        # validate merge Tag
                        for _mt in _reqMTag:
                            _mtagValue = _mergeTagData.get(f"{_mt[0]}_{_mt[1]}","")
                            _isValid,message = validateMtag(_mt,_mtagValue)
                            if _isValid:
                                _parseMTag[f"{_mt[0]}_{_mt[1]}"] = _mtagValue
                            else:
                                _errorTag[f"{_mt[0]}_{_mt[1]}"] = message
                                isError = True
                        if isError:
                            content = {'mergeTagData': _errorTag,'message': 'Some Value of Merge Tag is not Correct.','isError': True}
                            return Response(content,status=status.HTTP_200_OK)
                       

                        _gInst = inst.generateImageWithMTagRealtime(_parseMTag,generationType=1)[2]
                        _fData =  self.serializer_class(_gInst,context={'request': request}).data
                        return Response({"result": _fData,'isError': False},status=status.HTTP_200_OK)

                    except Exception as e:
                        content = {'mergeTagData': [f'This field is not Valid.\n{e} {str(traceback.format_exc())}'],'isError': True}
                        return Response(content,status=status.HTTP_200_OK)
                else:
                    content = {'message': "Image is not personalised.",'isError': True}
                    return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'message': "Image is not Generated.",'isError': True}
                return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'message': 'Object Doestnot Exist','isError': True}
            return Response(content,status=status.HTTP_200_OK)

from base64 import b64decode
def imageCreatorThubmnailFileView(request, slugs):
    _type = convertInt(request.GET.get('type','0'))
    try:
        _eid = slugs[IMAGECREATORGENERATED_UUID_TOTAL_NO:]
        _uid = slugs[:IMAGECREATORGENERATED_UUID_TOTAL_NO]
        _inst = None
        if _type == 1:
            _inst = ImageCreator.objects.get(id=int(str(b64decode(_eid),'utf-8')))
        else:
            _inst = ImageCreatorGenerated.objects.get(id=int(str(b64decode(_eid),'utf-8')))
        if str(_inst._uid)[:IMAGECREATORGENERATED_UUID_TOTAL_NO] == _uid:
            thumbnailPath = _inst.thumbnail.path
            isFound = os.path.isfile(thumbnailPath)
            if isFound:
                img = open(thumbnailPath,'rb')
                return FileResponse(img)
    except:
        pass

    # if thumbnail not exist return default
    _thumbnailPath = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'404_with_reload.jpg')
    return FileResponse(open(_thumbnailPath,'rb'))
    