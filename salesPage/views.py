import json
from threading import Thread
from django import conf
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from uuid import UUID,uuid1

import random,os
import shutil
from events import fire

from userlibrary.serializers import FileUploadSerializer
from userlibrary.models import FileUpload
from utils.customValidators import isValidUrl
from utils.common import convertInt
from newVideoCreator import models as TempVideoCreatorModels

from salesPage.models import (
    SALESPAGE_APP_TYPE, ButtonDataEditor, CrouselEditor, SalesPageEditor,
    SalesPageDetails, VideoCreatorTracking
)
from salesPage.serializers import (
    SalesPageEditorSerializer,TextEditorSerializer,
    ImageEditorSerializer,ButtonEditorSerializer,
    IconEditorSerializer,VideoEditorSerializer,SalesPageDetailsSerializer,
    SalesPageListSerializer,SalesPagePublicListSerializer
)

class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50



class SalesPageDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalesPageDetailsSerializer

    def get_object(self, pk,user):
        try:
            return (True,SalesPageEditor.objects.get(pk=pk,user=user))
        except SalesPageEditor.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if inst.isPublish==False and inst.isPublic == False:
            content = {'message': 'Cannot Access Details Without Publish.','isError': True}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)
        if is_exist:
            
            try:
                cinst = SalesPageDetails.objects.get(salesPage=inst)
            except:
                try:
                    newId = SalesPageDetails.objects.latest('id').id
                except:
                    newId = 0

                #newId = random.randint(newId,newId+1000)
                cinst = SalesPageDetails(salesPage=inst,pageLink=f'my-page-{newId}')
                cinst.save()

            sData = self.serializer_class(cinst,context={'request': request}).data
            sData['mergeTag'] = inst.getUsedMergeTag()
        
            sSData = SalesPageListSerializer(inst,context={'request': request}).data
            sData['name'] = sSData['name']
            sData['previewImage'] = sSData['previewImage']
            content = {'result': sData}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        
    def put(self, request,pk, format=None):
        #fields = ('id','name', 'textEditor','imageEditor','iconEditor','videoEditor','buttonEditor','crouselEditor')
        user = request.user
        data = request.data.copy()
        is_exist,inst = self.get_object(pk,user)
        if inst.isPublish==False and inst.isPublic == False:
            content = {'message': 'Cannot Access Details Without Publish.','isError': True}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)
        if is_exist:
            try:
                cinst = SalesPageDetails.objects.get(salesPage=inst)
            except:
                try:
                    newId = SalesPageDetails.objects.latest('id').id
                except:
                    newId = 0
                newId = random.randint(newId,newId+1000)
                cinst = SalesPageDetails(salesPage=inst,pageLink=f'my-page-{newId}')
                cinst.save()

            isCError = False
            errorMsg = []
            favicon = data.pop('favicon','')
            pageLink = data.pop('pageLink','')
            name = data.pop('name','')
            if pageLink:
                data['pageLink'] = pageLink.lower()
            fav_inst = None
            
            if favicon:
                try:
                    fav_inst = FileUpload.objects.get(id=int(favicon),user=user)
                    if fav_inst.media_type.split('/')[0] != 'image':
                        isCError = True
                        errorMsg.append('Image is Not Valid Type')
                except:
                    isCError=True
                    errorMsg.append('Object Not Exist')

            serializer = self.serializer_class(cinst, data=data,partial=True,context={'request': request})
            isValid = serializer.is_valid()
            if isValid and (not isCError):
                cinst = serializer.save()
                if favicon and fav_inst!='':
                    cinst.favicon = fav_inst
                    cinst.save()
                if favicon==None:
                    cinst.favicon = None
                    cinst.save()
                if name:
                    inst.name = name
                    inst.save()
                sData = self.serializer_class(cinst,context={'request': request}).data
                sData['mergeTag'] = inst.getUsedMergeTag()
                sSData = SalesPageListSerializer(inst,context={'request': request}).data
                sData['name'] = sSData['name']
                sData['previewImage'] = sSData['previewImage']
                content = {'result': sData}
                return Response(content,status=status.HTTP_200_OK)
            else:
                allErr = {}
                if not isValid:
                    allErr = serializer.errors
                if isCError:
                    allErr['favicon'] = errorMsg
                return Response(allErr,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)




class SalesPagePublicTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalesPagePublicListSerializer

    def get(self, request, format=None):
        
        data = request.GET
        orderId = data.get('order','')
        filter = data.get('filter','')
        validOrder = {1: 'name',2: '-timestamp',3: 'timestamp',4: '-updated'}
        isOrder = None
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = SalesPageEditor.objects.filter(isPublish=True,isPublic=True,name__icontains=filter)
        else:
            queryset = SalesPageEditor.objects.filter(isPublish=True,isPublic=True)
        if isOrder != None:
            queryset = queryset.order_by(isOrder)
        
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)




class SalesPageTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalesPageEditorSerializer

    def get(self, request, format=None):
        user = request.user
        ##manage ordering and filter
        data = request.GET
        isPublish = convertInt(data.get('isPublish',1),default=1)
        appType = convertInt(data.get('appType',0))
        

        orderId = data.get('order',3)
        filter = data.get('filter','')
        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = SalesPageEditor.objects.filter(user=user,name__icontains=filter)
        else:
            queryset = SalesPageEditor.objects.filter(user=user)
        if isOrder != None:
            queryset = queryset.order_by(isOrder)
        if appType==0:
            queryset = queryset.filter(appType=0)
            if isPublish == 0:
                queryset = queryset.filter(isPublish=False)
            else:
                queryset = queryset.filter(isPublish=True)
        else:
            queryset = queryset.filter(appType=1,isPublish=True)
    
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = SalesPageListSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



    def post(self, request, format=None):
        user = request.user
        data = request.data

        if not user.is_staff:
            content = {'detail': 'User does not have enough permission'}
            return Response(content,status=status.HTTP_401_UNAUTHORIZED)
            
        errors = {"crouselEditor": []}
        isError = False
        crouselEditorInst = []
        if 'crouselEditor' in data:
            crouselEditor = data.pop('crouselEditor')
            for cdata in crouselEditor:
                if 'crouselData' in cdata:
                    crosData = []
                    crosErrorData = []

                    ccdata = cdata['crouselData']
                    if len(ccdata)==0:
                        crosData.append({})
                        crosErrorData.append({})
                    else:
                        for singleFileInst in ccdata:
                            if 'id' in singleFileInst:
                                try:
                                    inst = FileUpload.objects.get(id=singleFileInst['id'],user=user)
                                    crosData.append(inst)
                                    crosErrorData.append({})
                                except:
                                    crosErrorData.append({"id": singleFileInst['id'],'detail': ["object not found."]})
                                    isError = True
                            else:
                                crosErrorData.append({"id": ["This field is required."]})
                                isError = True
                    errors['crouselEditor'].append({'crouselData': crosErrorData})
                    crouselEditorInst.append(crosData)
                else:
                    errors["crouselEditor"].append({"crouselData": ["This field is required."]})
                    isError = True
        if isError:
            return Response(errors,status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=data)
        isPublish = data.get('isPublish',False)
        if serializer.is_valid():
            currInst = serializer.save(user=user,isPublish=isPublish)
            for crinst in crouselEditorInst:
                ccInst = CrouselEditor.objects.create()
                if crinst!=[{}]:
                    ccInst.crouselData.add(*crinst)
                    ccInst.save_order({i.id: ind for ind,i in enumerate(crinst)})
                currInst.crouselEditor.add(ccInst)
            serializer.context['request']=request
            return Response(serializer.data)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)



class SalesPagePublicIdView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalesPageEditorSerializer

    def get_object(self, pk,user):
        try:
            return (True,SalesPageEditor.objects.get(pk=pk,user=user))
        except SalesPageEditor.DoesNotExist:
            return (False,'')


    def get(self, request,pk, format=None):
        user = request.user
        
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            return Response(inst.publicId,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)




class SalesPageDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalesPageEditorSerializer
    MAX_BUTTON_LEN = 10
    ALL_APP_TYPE = {ii[0]: True for ii in SALESPAGE_APP_TYPE}

    def get_object(self, pk,user):
        try:
            return (True,SalesPageEditor.objects.get(pk=pk,user=user))
        except SalesPageEditor.DoesNotExist:
            return (False,'')

    def getAllObject(self, pk,user):
        try:
            inst = SalesPageEditor.objects.get(pk=pk)
            if inst.isPublic:
                return (True,inst)
            elif inst.user.id == user.id:
                return (True,inst)
            else:
                return (False,'')
        except SalesPageEditor.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        
        is_exist,inst = self.getAllObject(pk,user)
        if is_exist:
            serializer = self.serializer_class(inst)
            serializer.context['request']=request
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        
    def put(self, request,pk, format=None):
        #fields = ('id','name', 'textEditor','imageEditor','iconEditor','videoEditor','buttonEditor','crouselEditor')
        user = request.user
        reqData = request.data.copy()
        is_exist,inst = self.get_object(pk,user)

        errors = {"textEditor": [],"imageEditor": [],"iconEditor": [],"videoEditor": [],'buttonEditor': [],"crouselEditor": []}
        isError = False
        if is_exist:
            isChange = False
            if inst.isPublish==True and inst.isPublic == False:
                content = {'message': 'Cannot Modify Publish Page.','isError': True}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)

            # handle appType
            # _appType = reqData.pop('appType',None)
            # if _appType !=None:
            #     try:
            #         if self.ALL_APP_TYPE[_appType]:
            #             inst.appType = _appType
            #             isChange = True
            #     except:
            #         pass
            prevData = json.dumps(self.serializer_class(inst,context={'request': request}).data)


            isThemeConfig = False
            themeColorConfig =  reqData.pop('themeColorConfig',None)
            if themeColorConfig!=None:
                try:
                    themeColorConfig = json.dumps(themeColorConfig)
                    isThemeConfig = True
                except:
                    pass


            isPublish =  reqData.pop('isPublish',None)
            if isPublish!=None:
                try:
                    isPublish = bool(isPublish)
                except:
                    pass
            
            ## must be done in frontend but unfortunate not done(check valid url)
            if 'buttonEditor' in reqData:
                try:
                    buttonEditor = reqData['buttonEditor']
                    for buttonDataI in buttonEditor:
                        if 'buttonData' in buttonDataI:
                            _newButtonEditors = buttonDataI["buttonData"]
                            for _buttonEditor in _newButtonEditors:
                                if "link" in _buttonEditor:
                                    isValid,_newUrl = isValidUrl(_buttonEditor["link"])
                                    if isValid:
                                        _buttonEditor["link"] = _newUrl
                except:
                    pass

            if 'buttonEditor' in reqData:
                try:
                    buttonEditor = reqData['buttonEditor']
                    for buttonDataI in buttonEditor:
                        if 'buttonData' in buttonDataI:
                            _newButtonEditors = buttonDataI["buttonData"]
                            for _buttonEditor in _newButtonEditors:
                                if "link" in _buttonEditor:
                                    isValid,_newUrl = isValidUrl(_buttonEditor["link"])
                                    if isValid:
                                        _buttonEditor["link"] = _newUrl
                except:
                    pass

            if 'imageEditor' in reqData:
                try:
                    _imageEditors = reqData['imageEditor']
                    for _imageEditor in _imageEditors:
                        if "image" in _imageEditor:
                            isValid,_newImgUrl = isValidUrl(_imageEditor["image"])
                            if isValid:
                                _imageEditor["image"] = _newImgUrl
                        if "imgUrl" in _imageEditor:
                            isValid,_newImgUrl = isValidUrl(_imageEditor["imgUrl"])
                            if isValid:
                                _imageEditor["imgUrl"] = _newImgUrl
                except:
                    pass
            
            if 'iconEditor' in reqData:
                try:
                    _iconEditors = reqData['iconEditor']
                    for _iconEditor in _iconEditors:
                        if "image" in _iconEditor:
                            isValid,_newImgUrl = isValidUrl(_iconEditor["image"])
                            if isValid:
                                _iconEditor["image"] = _newImgUrl
                        if "link" in _iconEditor:
                            isValid,_newImgUrl = isValidUrl(_iconEditor["link"])
                            if isValid:
                                _iconEditor["link"] = _newImgUrl
                except:
                    pass

            serializer = self.serializer_class(inst,data=reqData,partial=True)
            if serializer.is_valid():
                if 'name' in reqData:
                    inst.name = reqData['name']
                    isChange = True
                if isThemeConfig:
                    inst.themeColorConfig = themeColorConfig
                    isChange = True
                if isPublish!= None:
                    inst.isPublish = isPublish
                    isChange = True
                if isChange:
                    inst.save()


                if 'crouselEditor' in reqData:
                    crouselEditor = reqData['crouselEditor']

                    for data in crouselEditor:
                        try:
                            if 'id' in data:
                                tinst = inst.crouselEditor.get(id=data['id'])
                                if 'isDeleted' in data:
                                    isDeleted = None
                                    if data['isDeleted']:
                                        isDeleted = True
                                    else:
                                        isDeleted = False
                                    if tinst.isDeleted != isDeleted:
                                        tinst.isDeleted = isDeleted
                                        tinst.save()

                                if 'crouselData' in data:
                                    crosData = []
                                    crosErrorData = []
                                    ccdata = data['crouselData']
                                    if len(ccdata)==0:
                                        crosData.append({})
                                        crosErrorData.append({})
                                    else:
                                        for singleFileInst in ccdata:
                                            if 'id' in singleFileInst:
                                                try:
                                                    inst_ = FileUpload.objects.get(id=singleFileInst['id'],user=user)
                                                    crosData.append(inst_)
                                                    crosErrorData.append({})
                                                except:
                                                    crosErrorData.append({"id": singleFileInst['id'],'detail': ["object not found."]})
                                                    isError = True
                                            else:
                                                crosErrorData.append({"id": ["This field is required."]})
                                                isError = True
                                    errors['crouselEditor'].append({'crouselData': crosErrorData})
                                    tinst.crouselData.clear()
                                    tinst.crouselData.add(*crosData)
                                    tinst.save_order({i.id: ind for ind,i in enumerate(crosData)})

                            else:
                                errors["crouselEditor"].append({"id": ["This field is required."]})
                        except Exception as e:
                            errors["crouselEditor"].append({"id": ["Object Doesnot exist."]})

                if 'buttonEditor' in reqData:
                    buttonEditor = reqData['buttonEditor']

                    for data in buttonEditor:
                        try:
                            if 'id' in data:
                                tinst = inst.buttonEditor.get(id=data['id'])
                                if 'isDeleted' in data:
                                    isDeleted = None
                                    if data['isDeleted']:
                                        isDeleted = True
                                    else:
                                        isDeleted = False
                                    if tinst.isDeleted != isDeleted:
                                        tinst.isDeleted = isDeleted
                                        tinst.save()

                                if 'buttonData' in data:
                                    crosErrorData = []
                                    buttonData = data['buttonData'][:self.MAX_BUTTON_LEN]
                                    allitinst = list(tinst.buttonData.all())
                                    previousLenButton = len(allitinst)
                                    newButtonData = []
                                    notAddedButtonData = []
                                    for indxbt,idata in enumerate(buttonData[:previousLenButton]):
                                        try:
                                            tempS = ButtonEditorSerializer(allitinst[indxbt],data=idata)
                                            if tempS.is_valid():
                                                newButtonData.append(tempS.save())
                                                crosErrorData.append({})
                                            else:
                                                crosErrorData.append(tempS.errors)
                                                notAddedButtonData.append(allitinst[indxbt])
                                                isError = True
                                        except Exception as e:
                                            notAddedButtonData.append(allitinst[indxbt])
                                            crosErrorData.append({"id": ["This field is required."]})
                                    if len(buttonData)<=previousLenButton:
                                        for indxbt in range(len(buttonData),previousLenButton):
                                            notAddedButtonData.append(allitinst[indxbt])
                                    for indxbt in notAddedButtonData:
                                        indxbt.delete()

                                    for idata in buttonData[previousLenButton:]:
                                        try:
                                            tempS = ButtonEditorSerializer(data=idata)
                                            if tempS.is_valid():
                                                newButtonData.append(tempS.save())
                                                crosErrorData.append({})
                                            else:
                                                crosErrorData.append(tempS.errors)
                                                isError = True
                                        except Exception as e:
                                            crosErrorData.append({"id": ["This field is required."]})
                                    errors['buttonEditor'].append(crosErrorData)
                                    tinst.buttonData.clear()
                                    tinst.buttonData.add(*newButtonData)
                                    
                            else:
                                errors["buttonEditor"].append({"id": ["This field is required."]})
                        except Exception as e:
                            print(e)
                            errors["buttonEditor"].append({"id": ["Object Doesnot exist."]})

                if 'videoEditor' in reqData:
                    videoEditor = reqData['videoEditor']
                    for data in videoEditor:
                        try:
                            tinst = inst.videoEditor.get(id=data['id'])
                            tempS = VideoEditorSerializer(tinst,data=data)
                            if tempS.is_valid():
                                tempS.save()
                                errors['videoEditor'].append({})
                            else:
                                errors['videoEditor'].append(tempS.errors)
                                isError = True
                        except Exception as e:
                            print(e)
                            errors['videoEditor'].append({"id": ['This field is required']})
                            isError = True

                if 'iconEditor' in reqData:
                    iconEditor = reqData['iconEditor']
                    for data in iconEditor:
                        try:
                            tinst = inst.iconEditor.get(id=data['id'])
                            tempS = IconEditorSerializer(tinst,data=data)
                            if tempS.is_valid():
                                tempS.save()
                                errors['iconEditor'].append({})
                            else:
                                errors['iconEditor'].append(tempS.errors)
                                isError = True
                        except Exception as e:
                            print(e)
                            errors['iconEditor'].append({"id": ['This field is required']})
                            isError = True

                if 'imageEditor' in reqData:
                    imageEditor = reqData['imageEditor']
                    for data in imageEditor:
                        try:
                            tinst = inst.imageEditor.get(id=data['id'])
                            tempS = ImageEditorSerializer(tinst,data=data)
                            if tempS.is_valid():
                                tempS.save()
                                errors['imageEditor'].append({})
                            else:
                                errors['imageEditor'].append(tempS.errors)
                                isError = True
                        except Exception as e:
                            print(e)
                            errors['imageEditor'].append({"id": ['This field is required']})
                            isError = True

                if 'textEditor' in reqData:
                    textEditor = reqData['textEditor']
                    for data in textEditor:
                        try:
                            tinst = inst.textEditor.get(id=data['id'])
                            tempS = TextEditorSerializer(tinst,data=data)
                            if tempS.is_valid():
                                tempS.save()
                                errors['textEditor'].append({})
                            else:
                                errors['textEditor'].append(tempS.errors)
                                isError = True
                        except Exception as e:
                            print(e)
                            errors['textEditor'].append({"detail": ['id and content field is required']})
                            isError = True
                            
                print(errors)
                serializer = self.serializer_class(inst)
                serializer.context['request']=request
                newData = serializer.data

                if prevData != newData and inst.isPublic == False:
                    ## set thubmnail
                    
                    token = request.META.get('HTTP_AUTHORIZATION','')
                    if token:
                        token = token.replace("Token ","")

                    url = settings.FRONTEND_URL + f'/preview/salespage/{inst.id}?token={token}'
                    outputPath = inst.previewImage.path
                    uuidName = os.path.basename(outputPath)
                    try:
                        isValidUUid = UUID(uuidName.split('.')[0])
                        isFound = os.path.isfile(outputPath)
                        _oldOutputPath = outputPath
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        if isFound:
                            shutil.move(_oldOutputPath,outputPath)
    
                    except:
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                    inst.previewImage = outputPath.split(settings.MEDIA_ROOT)[1]
                    inst.save()
                    data = {"type": "setSalesPageCampaignThumbnail","data": {"url": url,"outputPath": outputPath}}
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "generateThumbnail",
                        {
                            "type": "setThumbnail",
                            "text": data,
                        },
                    )
                    _data = serializer.data

                # handle merge tag on publish
                if isPublish:
                    inst.setMergeTag()
                    
                # send websocket response to newvideocreator
                if inst.appType == 1 and isPublish:
                    _data = serializer.data
                    _vidInst = VideoCreatorTracking.objects.filter(salespage=inst)
                    _data["_url"] = settings.VIDEO_CREATOR_URL
                    _data["video_id"] = None
                    if _vidInst:
                        _vidInst = _vidInst.first()
                        _data["video_id"] = _vidInst.videoCreator.pk
                        _data["_url"] = _vidInst.origin

                    commandData = SalesPageListSerializer(inst,context={'request': request}).data
                    fire.eventFire(user,"sharingPage.add",commandData)
                    
                return Response(_data,status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


    def delete(self,request,pk):
        
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            name = inst.name
            if inst.isPublic == False and inst.isDefault==False:
                commandData = {"id": inst.id}
                inst.delete()
                if inst.appType == 1 and inst.isPublish:
                    fire.eventFire(user,"sharingPage.remove",commandData)
                    _th = Thread(target= TempVideoCreatorModels.globalDeleteSharingPage)
                    _th.start()
                content = {'name': name,'isError': False}
            else:
                content = {'name': name,'isError': True}
                if inst.isDefault:
                    content["message"] = "Default Template Cannot be Deleted."
                else:
                    content["message"] = "Public Page Cannot be Deleted."

            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': False}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class SalesPageCopyView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalesPageEditorSerializer
    ALL_APP_TYPE = {ii[0]: True for ii in SALESPAGE_APP_TYPE}

    def get_object(self, pk,user):
        try:
            currntInst = SalesPageEditor.objects.get(pk=pk)
            return (True,currntInst)
        except SalesPageEditor.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        data = request.GET
        appType = convertInt(data.get('appType',0))
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if inst.user.id==user.id or inst.isPublic:
                # dump data for new video editor
                _videoInst=None
                if appType==1:
                    _videoId = convertInt(data.get("video_id",None))
                    if _videoId:
                        # validate VideoId
                        _origin = request.META.get("HTTP_ORIGIN",settings.VIDEO_CREATOR_URL)
                        if not _origin:
                            _origin = request.META.get("HTTP_REFERER",settings.VIDEO_CREATOR_URL)
                        try:
                            _videoInst = TempVideoCreatorModels.TempVideoCreator.objects.get(pk=_videoId,user=user)
                        except:
                            content = {'video_id': ["This Field is Not Valid."]}
                            return Response(content,status=status.HTTP_200_OK)
                    else:
                        content = {'video_id': ["This Field is Required."]}
                        return Response(content,status=status.HTTP_200_OK)
                


                serializerData = self.serializer_class(inst,context={'request': request}).data
                serializerData.pop('publicId')

                serializerData['name'] = f"Copy of {serializerData['name']}"
                serializerData.pop('themeColorConfig')
                #themeColorConfig = json.dumps(serializerData.pop('themeColorConfig'))
                
                newSerializer = self.serializer_class(data=serializerData,context={'request': request})
                if newSerializer.is_valid():
                    currInst = newSerializer.save(user=user,themeColorConfig=inst.themeColorConfig)
                    for crinst in serializerData['crouselEditor']:
                        ccInst = CrouselEditor.objects.create(isDeleted=crinst['isDeleted'])
                        allCrouselItem = [singleFile['id'] for singleFile in crinst["crouselData"]]
                        ccInst.crouselData.add(*allCrouselItem)

                        currInst.crouselEditor.add(ccInst)
                    currInst.publicId = inst.publicId
                    currInst.previewImage = inst.previewImage
                    currInst.isPublish = False
                    if appType==1:
                        currInst.appType = 1
                        _inst,ct = VideoCreatorTracking.objects.get_or_create(salespage=currInst,videoCreator=_videoInst,origin=_origin)
                    currInst.save()
                    
                    token = request.META.get('HTTP_AUTHORIZATION','')
                    if token:
                        token = token.replace("Token ","")
                    else:
                        token = user.getToken()

                    url = settings.FRONTEND_URL + f'/preview/salespage/{currInst.id}?token={token}'
                    outputPath = currInst.previewImage.path
                    uuidName = os.path.basename(outputPath)
                    try:
                        isValidUUid = UUID(uuidName.split('.')[0])
                        isFound = os.path.isfile(outputPath)
                        if isFound:
                            _prevPath = outputPath
                            #os.remove(outputPath)
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        if isFound:
                            shutil.copy(_prevPath,outputPath)
                    except:
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                    currInst.previewImage = outputPath.split(settings.MEDIA_ROOT)[1]
                    currInst.save()
                    data = {"type": "setSalesPageCampaignThumbnail","data": {"url": url,"outputPath": outputPath}}
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "generateThumbnail",
                        {
                            "type": "setThumbnail",
                            "text": data,
                        },
                    )

                    content = {'result': newSerializer.data}
                    return Response(content,status=status.HTTP_200_OK)
                else:
                    return Response(newSerializer.errors,status=status.HTTP_400_BAD_REQUEST)
                
        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)
        

