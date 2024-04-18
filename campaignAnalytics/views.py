from django.db import reset_queries
from django.db.models.expressions import Random
from campaign.models import GroupCampaign, GroupSingleCampaign, SoloCampaign
from django.conf import settings
from rest_framework import serializers, status

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q
from django.db.models import Subquery
import os,json
from functools import reduce

from django.contrib.postgres.aggregates import ArrayAgg
from datetime import datetime
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from random import randint

from campaign.models import MainCampaign

from campaignAnalytics.models import (
    CampaignSingleAnalytics,CampaignGroupAnalytics, CombinedAnalytics,
    CampaignProspect,CampaignEmailOpenedAnalytics,CampaignVideoPlayedAnalytics,
    CampaignSentAnalytics,CampaignOpenAnalytics,CampaignCtaClickedtAnalytics,
    CampaignCollateralClickedtAnalytics

)

from campaignAnalytics.serializers import (
    CombinedAnalyticsSignalSerializer,CampaignProspectSerializer,
    CampaignSoloBriefSerializer,CampaignGroupBriefSerializer,
    CampaignAllBriefSerializer,DashboardProspectSerializer,
    DashProspectSerializer,CampaignGroupDetailsSerializer
)





class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50

    

from django.http import FileResponse
from campaignAnalytics.models import CampaignGroupAnalytics
from newVideoCreator import models as newVideoCreatorModels

class CampaignThumbnailViews(APIView,LimitOffset):
    permission_classes = (AllowAny,)

    def get_object(self, pk,uid):
        try:
            inst = GroupCampaign.objects.get(pk = pk)
            try:
                return (True,GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=uid),inst)
            except:
                return (False,'','')
        except:
            return (False,'','')

    def get_mainVideo_obj(self,slug):
        try:
            _inst = newVideoCreatorModels.TempVideoCreator.objects.get(slug=slug)
            return (2,_inst)
        except:
            return self.get_group_handler(slug)
        

    def get_mainVideoGenerate_obj(self,videoCreatorInst,uniqueIdentity):
        try:
            _inst = newVideoCreatorModels.MainVideoGenerate.objects.get(videoCreator=videoCreatorInst,uniqueIdentity__iexact=uniqueIdentity)
            return (True,_inst)
        except:
            pass
        return (False,None)


    def get_group_handler(self,uid):
        try:
            return (True,newVideoCreatorModels.GroupHandler.objects.get(id=uid))
        except:
            return (False,"")

    def get_video_generate(self,uid):
        try:
            return (True,newVideoCreatorModels.MainVideoGenerate.objects.get(id=uid))
        except:
            return (False,'')

    def get_video_generate_batch(self,uid,uniqueIdentity=False):
        try:
            _inst = newVideoCreatorModels.GroupHandler.objects.get(id=uid)
            if uniqueIdentity:
                _inst = newVideoCreatorModels.MainVideoGenerate.objects.get(groupHandlerTracker=_inst,uniqueIdentity=uniqueIdentity)
            return (True,_inst)
        except:
            return (False,'')

    def get(self, request, format=None):

        open('/home/govind/thumbnailOpenLog.txt','a').write(f"{datetime.now()} => {request.META}\n")
        data = request.GET
        campaignId = data.get('campaign','')
        uid = data.get('uid','')
        isPlayBtn = data.get('isPlayBtn',False)


        appType = 0
        is_exist=False
        inst=None
        thumbnailPath = None
        is_exist,_videoCreatorObj = self.get_mainVideo_obj(campaignId)
        if is_exist == 2 and uid:
            appType = 1
            is_exist,inst = self.get_mainVideoGenerate_obj(_videoCreatorObj,uid)
            if not is_exist:
                is_exist = True
                inst = _videoCreatorObj
        elif is_exist:
            appType = 1
            inst = _videoCreatorObj

        elif uid and campaignId:
            if uid == 'video_creator':
                is_exist,inst = self.get_video_generate(campaignId)
                appType = 1
            elif uid[-9:] == '__batch__':
                # new video creator batch mail
                _uniqueIdentity = uid[:-9]
                is_exist,inst = self.get_video_generate_batch(campaignId,uniqueIdentity=_uniqueIdentity)
                appType = 1
            else:
                is_exist,inst,camp = self.get_object(campaignId,uid)


        if is_exist:
            if appType==1:
                thumbnailPath = inst.thumbnail.path
                isFound = False
                if isPlayBtn:
                    newThumbnailP = thumbnailPath.replace('.jpeg','_play.jpeg')
                    if os.path.isfile(newThumbnailP):
                        thumbnailPath = newThumbnailP
                        isFound = True
                if not isFound:
                    isFound = os.path.isfile(thumbnailPath)
                if not isFound:
                    Response("0",status=status.HTTP_400_BAD_REQUEST)
            else:
                inst_ = CampaignGroupAnalytics(campaign=inst,command=1)
                thumbnailPath = inst.genVideo.thumbnailImage.path
                if inst.thumbnail:
                    isFound = os.path.isfile(inst.thumbnail.path)
                    if isFound and inst.thumbnail.name != inst._meta.get_field('thumbnail').get_default():
                        thumbnailPath = inst.thumbnail.path
                inst_.save()
            img = open(thumbnailPath,'rb')
            return FileResponse(img)
        return Response("0",status=status.HTTP_400_BAD_REQUEST)

def decryptData(endata,secret):
    code = [int(endata[i:i+2],16) for i in range(0, len(endata), 2)]
    bitData = reduce((lambda a, b: a ^ b), list(map(ord,secret)))
    return ''.join([chr(bitData^i) for i in code])

'''
const cipher = salt => {
    const textToChars = text => text.split('').map(c => c.charCodeAt(0));
    const byteHex = n => ("0" + Number(n).toString(16)).substr(-2);
    const applySaltToChar = code => textToChars(salt).reduce((a,b) => a ^ b, code);

    return text => text.split('')
        .map(textToChars)
        .map(applySaltToChar)
        .map(byteHex)
        .join('');
}


// To create a cipher
const myCipher = cipher('mySecretSalt')

//Then cipher any text:
myCipher('the secret string')   // --> "7c606d287b6d6b7a6d7c287b7c7a61666f"

//To decipher, you need to create a decipher and use it:
const myDecipher = decipher('mySecretSalt')
myDecipher("7c606d287b6d6b7a6d7c287b7c7a61666f")    // --> 'the secret string'

type:
    0: solo
    1: group

command = (
    (0,'SENT'),
    (2,'OPENED'),
    (3,'VIDEO PLAYED'),
    (4,'CTA CLICKED'),
    (5,'CROUSEL CLICKED')
)

command == 0 
    # copy solo link
    data = {'type': 0,'command': 0,'data': ''}
    #copy group code
    data = {'type': 1,'command': 0,'data': ''}


command == 2
    # solo
    data = {'type': 0,'command': 2,'data': ''}
    # group
    data = {'type': 1,'command': 2,'data': '', 'uid': 'email'}


command == 3
    # solo
    data = {'type': 0,'command': 3,'data': '0'}
    # group
    data = {'type': 1,'command': 3,'data': '0', 'uid': 'email'} 

command == 4
    # solo
    data = {'type': 0,'command': 4,'data': 'button id'}
    # group
    data = {'type': 1,'command': 4,'data': 'button id', 'uid': 'email'} 

command == 5
    # solo
    data = {'type': 0,'command': 5,'data': 'file id'}
    # group
    data = {'type': 1,'command': 5,'data': 'file id', 'uid': 'email'} 

'''


class EventCollectingView(APIView,LimitOffset):
    permission_classes = (AllowAny,)

    def get(self, request,data, format=None):
        try:
            key,data = data[-32:],data[:-32]
            data = json.loads(decryptData(data,key))
            pk = f"{key[:8]}-{key[8:12]}-{key[12:16]}-{key[16:20]}-{key[20:]}"
            try:
                type_ = int(data.get('type'))
                command =  int(data.get('command'))
                # solo
                if type_ == 0:
                    inst = SoloCampaign.objects.get(id=pk)
                    if command == 0:
                        inst_ = CampaignSingleAnalytics(campaign=inst,command=0)
                        inst_.save()
                    elif command == 2:
                        inst_ = CampaignSingleAnalytics(campaign=inst,command=2)
                        inst_.save()
                    elif command == 3:
                        vdata = float(data.get('data'))
                        if 0<=vdata<=10000:
                            inst_ = CampaignSingleAnalytics(campaign=inst,command=3,data=str(vdata),cData=json.dumps({'name': inst.genVideo.name}))
                            inst_.save()

                    elif command == 4:
                        vdata = int(data.get('data'))
                        salespageD = json.loads(inst.salesPageData)
                        for i in salespageD['buttonEditor']:
                            for j in i['buttonData']:
                                if vdata == j['id']:
                                    inst_ = CampaignSingleAnalytics(campaign=inst,command=4,data=str(vdata),cData=json.dumps(j))
                                    inst_.save()
                                    return Response('',status=status.HTTP_200_OK)

                    elif command == 5:
                        vdata = int(data.get('data'))
                        salespageD = json.loads(inst.salesPageData)
                        for i in salespageD['crouselEditor']:
                            for j in i['crouselData']:
                                if vdata == j['id']:
                                    inst_ = CampaignSingleAnalytics(campaign=inst,command=5,data=str(vdata),cData=json.dumps(j))
                                    inst_.save()
                                    return Response('',status=status.HTTP_200_OK)

                    return Response('',status=status.HTTP_200_OK)

                # group
                elif type_ == 1:
                    inst = GroupCampaign.objects.get(id=pk)
                    if command == 0:
                        allCamp = GroupSingleCampaign.objects.filter(groupcampaign=inst)
                        tdata = []
                        for scamp in allCamp:
                            inst_ = CampaignGroupAnalytics(campaign=scamp,command=0)
                            inst_.save()
                            #tdata.append(inst_)
                        #fdata = CampaignGroupAnalytics.objects.bulk_create(tdata)
                    elif command == 2:
                        uid = data.get('uid')
                        inst1 = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=uid)
                        inst_ = CampaignGroupAnalytics(campaign=inst1,command=2)
                        inst_.save()
                    elif command == 3:
                        uid = data.get('uid')
                        vdata = float(data.get('data'))
                        if 0<=vdata<=10000:
                            inst1 = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=uid)
                            inst_ = CampaignGroupAnalytics(campaign=inst1,command=3,data=str(vdata),cData=json.dumps({'name': inst1.genVideo.name}))
                            inst_.save()

                    elif command == 4:
                        uid = data.get('uid')
                        vdata = float(data.get('data'))
                        inst1 = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=uid)
                        salespageD = json.loads(inst1.salesPageData)
                        for i in salespageD['buttonEditor']:
                            if i['isDeleted'] == False:
                                for j in i['buttonData']:
                                    if j['isDeleted'] == False:
                                        if vdata == j['id']:
                                            inst_ = CampaignGroupAnalytics(campaign=inst1,command=4,data=str(vdata),cData=json.dumps(j))
                                            inst_.save()
                                            return Response('',status=status.HTTP_200_OK)

                    elif command == 5:
                        uid = data.get('uid')
                        vdata = int(data.get('data'))
                        inst1 = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=uid)
                        salespageD = json.loads(inst1.salesPageData)

                        for i in salespageD['crouselEditor']:
                            if i['isDeleted'] == False:
                                for j in i['crouselData']:
                                    if vdata == j['id']:
                                        inst_ = CampaignGroupAnalytics(campaign=inst1,command=5,data=str(vdata),cData=json.dumps(j))
                                        inst_.save()
                                        return Response('',status=status.HTTP_200_OK)
                    return Response('',status=status.HTTP_200_OK)
                else:
                    return Response('',status=status.HTTP_200_OK)
            except Exception as e:
                print('ERror: ',e)
                return Response('',status=status.HTTP_200_OK)
        except Exception as e:
            print('Error: ',e)
            return Response('',status=status.HTTP_200_OK)


from aiQueueManager.models import VideoRenderMultipleScene
from salesPage.models import SalesPageEditor


class CampaignAnalyticsMainView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                allD = CampaignProspect.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            allD = CampaignProspect.objects.filter(campaign__user=user)

        if dfrom:
            allD = allD.filter(timestamp__gte=dfrom)
        if dto:
            allD = allD.filter(timestamp__lte=dto)

        mailSent = allD.filter(solom__isnull=True,isSent=True).count()
        mailOpened = allD.filter(solom__isnull=True,isMailedOpend=True).count()
        linkOpened = allD.filter(solom__isnull=True,isLinkedOpend=True).count()
        videoPlayed = allD.filter(solom__isnull=True,isVideoPlayed=True).count()

        tempCtaC = allD.filter(solom__isnull=True,isCtaClicked=True)
        ctaClicked = CampaignCtaClickedtAnalytics.objects.filter(cpros__in=tempCtaC.values_list('id',flat=True)).count()
        #ctaClicked = allD.filter(solom__isnull=True,isCtaClicked=True).count()
        tempCrosC = allD.filter(solom__isnull=True,isCollateral=True)
        crouselClicked = CampaignCollateralClickedtAnalytics.objects.filter(cpros__in=tempCrosC.values_list('id',flat=True)).count()
        #crouselClicked = allD.filter(solom__isnull=True,isCollateral=True).count()

        groupData = {'mailSent': mailSent,'mailOpened': mailOpened,'linkOpened': linkOpened,'videoPlayed': videoPlayed,'ctaClicked': ctaClicked,'crouselClicked': crouselClicked}

        linkSent = allD.filter(groupm__isnull=True,isSent=True).count()
        mailOpened = allD.filter(groupm__isnull=True,isMailedOpend=True).count()
        linkOpened = allD.filter(groupm__isnull=True,isLinkedOpend=True).count()
        videoPlayed = allD.filter(groupm__isnull=True,isVideoPlayed=True).count()

        tempCtaC = allD.filter(groupm__isnull=True,isCtaClicked=True)
        ctaClicked = CampaignCtaClickedtAnalytics.objects.filter(cpros__in=tempCtaC.values_list('id',flat=True)).count()
        #ctaClicked = allD.filter(groupm__isnull=True,isCtaClicked=True).count()
        tempCrosC = allD.filter(groupm__isnull=True,isCollateral=True)
        crouselClicked = CampaignCollateralClickedtAnalytics.objects.filter(cpros__in=tempCrosC.values_list('id',flat=True)).count()
        #crouselClicked = allD.filter(groupm__isnull=True,isCollateral=True).count()
        soloData = {'linkSent': linkSent,'linkOpened': linkOpened,'videoPlayed': videoPlayed,'ctaClicked': ctaClicked,'crouselClicked': crouselClicked}
        content = {'groupData': groupData,'soloData': soloData}
        if campaign:
            content['campaign_name']=inst.name
        else:
            content['totalVideos'] = VideoRenderMultipleScene.objects.filter(user=user,generateStatus__isnull=False).filter(generateStatus__isDefault=True).count()
            content['totalSalespages'] = SalesPageEditor.objects.filter(user=user).count()
            content['totalCampaign'] = MainCampaign.objects.filter(user=user).count()
        return Response(content,status=status.HTTP_200_OK)
    


class CampaignAnalyticsSignalView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,campaign=inst,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,campaign=inst,signalDeleted=False) 
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,campaign__user=user,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,campaign__user=user,signalDeleted=False)
        
        isRead = request.GET.get('isRead','')
        if isRead == '1':
            query = query.filter(isRead=True)
        elif isRead == '0':
            query = query.filter(isRead=False)
        filter_ = request.GET.get('filter','')
        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(cpros__uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass

        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)
        
        order = request.GET.get('order','')
        if order:
            try:
                cod = int(order)
                if cod == 0:
                    query = query.order_by('cpros__uniqueIdentity')
                elif cod == 1:
                    query = query.order_by('-cpros__uniqueIdentity')
                elif cod == 2:
                    query = query.order_by('timestamp')
                else:
                    query = query.order_by('-timestamp')
            except:
                query = query.order_by('-timestamp')
        else:
            query = query.order_by('-timestamp')

        results = self.paginate_queryset(query, request, view=self)
        serializer = CombinedAnalyticsSignalSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class CampaignAnalyticsSignalManageView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,campaign=inst,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,campaign=inst,signalDeleted=False) 
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,campaign__user=user,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,campaign__user=user,signalDeleted=False)

        filter_ = request.GET.get('filter','')
        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(cpros__uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass

        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        isRead = request.GET.get('isRead','')
        if isRead == '0':
            query.update(isRead=False)
        elif isRead == '1':
            query.update(isRead=True)
        return Response('',status=status.HTTP_200_OK)



class CampaignAnalyticsSignalDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,CombinedAnalytics.objects.get(pk=pk,campaign__user=user))
        except CombinedAnalytics.DoesNotExist:
            return (False,'')

    def post(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            isRead = request.data.get('isRead','')
            if isRead:
                inst.isRead = True
                inst.save()
            else:
                inst.isRead = False
                inst.save()
            return Response('',status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            inst.signalDeleted = True
            inst.save()
            return Response('',status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

from campaignAnalytics.models import PSTATUS
ALLPSTATUSK = []
for ii in PSTATUS:
    ALLPSTATUSK.append(ii[0])

class CampaignAnalyticsProspectView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignProspect.objects.filter(campaign=inst)#CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,campaign=inst,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,campaign=inst,signalDeleted=False) 
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignProspect.objects.filter(campaign__user=user) #CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,campaign__user=user,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,campaign__user=user,signalDeleted=False)

        filter_ = request.GET.get('filter','')

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(isMailedOpend=True)
                if 3 in category:
                    query = query.filter(isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(isCtaClicked=True)
                if 5 in category:
                    query = query.filter(isCollateral=True)
            except:
                pass


        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        prospectStatus = request.GET.get('prospectstatus','')
        if prospectStatus or prospectStatus == 0:
            try:
                allP = [int(i) for i in prospectStatus.split('_')]
                query = query.filter(prospectStatus__in=allP)
            except:
                return Response({'prospectStatus': ['This Field is not Valid.']},status=status.HTTP_400_BAD_REQUEST)


        type_ = request.GET.get('type','')
        if type_=='linksent':
            query = query.filter(groupm__isnull=True,isSent=True)
        elif type_=='mailsent':
            query = query.filter(solom__isnull=True,isSent=True)
        else:
            query = query.filter(Q(isMailedOpend=True) | Q(isLinkedOpend=True) | Q(isVideoPlayed=True) | Q(isCollateral=True) | Q(isCtaClicked=True))

        order = request.GET.get('order','')
        if order:
            try:
                cod = int(order)
                if cod == 0:
                    query = query.order_by('uniqueIdentity')
                elif cod == 1:
                    query = query.order_by('-uniqueIdentity')
                elif cod == 4:
                    query = query.order_by('timestamp')
                elif cod == 5:
                    query = query.order_by('-timestamp')
                elif cod == 2:
                    query = query.order_by('updated')
                else:
                    query = query.order_by('-updated')
            except:
                query = query.order_by('-updated')
        else:
            query = query.order_by('-updated')



        results = self.paginate_queryset(query, request, view=self)
        serializer = CampaignProspectSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)




from campaignAnalytics.models import PSTATUS
AllPStatus = []
for ii in PSTATUS:
    AllPStatus.append(ii[0])

class CampaignAnalyticsProspectDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def post(self, request,format=None):
        user = request.user
        uniqueIdentity = request.data.get('uniqueIdentity','')
        if not uniqueIdentity:
            return Response({'uniqueIdentity': ['This field is Required']},status=status.HTTP_400_BAD_REQUEST)
        try:
            pstatus = request.data.get('prospectStatus','')
            if pstatus or pstatus == 0:
                pstatus = int(pstatus)
                if pstatus in AllPStatus:
                    allSingleU = CampaignProspect.objects.filter(uniqueIdentity=uniqueIdentity,campaign__user=user)
                    allSingleU.update(prospectStatus = pstatus)
                    # for ii in allSingleU:
                    #     ii.prospectStatus = pstatus
                    #     ii.save()
                    return Response('',status=status.HTTP_200_OK)
                else:
                    return Response({'prospectStatus': ['This field is not Valid']},status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'prospectStatus': ['This field is Required']},status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'prospectStatus': ['This field is not Valid']},status=status.HTTP_400_BAD_REQUEST)




class CampaignSoloBriefView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignProspect.objects.filter(campaign=inst,groupm__isnull=True)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignProspect.objects.filter(campaign__user=user,groupm__isnull=True)

        filter_ = request.GET.get('filter','')

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(isMailedOpend=True)
                if 3 in category:
                    query = query.filter(isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(isCtaClicked=True)
                if 5 in category:
                    query = query.filter(isCollateral=True)
            except:
                pass
            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        order = request.GET.get('order','')
        if order:
            try:
                cod = int(order)
                if cod == 0:
                    query = query.order_by('uniqueIdentity')
                elif cod == 1:
                    query = query.order_by('-uniqueIdentity')
                elif cod == 2:
                    query = query.order_by('updated')
                elif cod == 4:
                    query = query.order_by('timestamp')
                elif cod == 5:
                    query = query.order_by('-timestamp')
                else:
                    query = query.order_by('-updated')
            except:
                query = query.order_by('-updated')
        else:
            query = query.order_by('-updated')


        results = self.paginate_queryset(query, request, view=self)
        serializer = CampaignSoloBriefSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class CampaignGroupDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,GroupCampaign.objects.get(pk=pk,campaign__user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('gcampaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignProspect.objects.filter(groupm__groupcampaign=inst,solom__isnull=True)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignProspect.objects.filter(campaign__user=user,solom__isnull=True)

        filter_ = request.GET.get('filter','')

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(isMailedOpend=True)
                if 3 in category:
                    query = query.filter(isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(isCtaClicked=True)
                if 5 in category:
                    query = query.filter(isCollateral=True)
            except:
                pass
            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        order = request.GET.get('order','')
        if order:
            try:
                cod = int(order)
                if cod == 0:
                    query = query.order_by('uniqueIdentity')
                elif cod == 1:
                    query = query.order_by('-uniqueIdentity')
                elif cod == 2:
                    query = query.order_by('updated')
                elif cod == 4:
                    query = query.order_by('timestamp')
                elif cod == 5:
                    query = query.order_by('-timestamp')
                else:
                    query = query.order_by('-updated')
            except:
                query = query.order_by('-updated')
        else:
            query = query.order_by('-updated')


        results = self.paginate_queryset(query, request, view=self)
        serializer = CampaignGroupDetailsSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


class CampaignGroupBriefView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignProspect.objects.filter(campaign=inst,solom__isnull=True)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignProspect.objects.filter(campaign__user=user,solom__isnull=True)

        filter_ = request.GET.get('filter','')

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(isMailedOpend=True)
                if 3 in category:
                    query = query.filter(isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(isCtaClicked=True)
                if 5 in category:
                    query = query.filter(isCollateral=True)
            except:
                pass
            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        order = request.GET.get('order','')
        query = query.distinct('groupm__groupcampaign__id').order_by('groupm__groupcampaign__id')
        if order:
            query = CampaignProspect.objects.filter(pk__in=Subquery(query.values('pk')))
            try:
                cod = int(order)
                if cod == 0:
                    query = query.order_by('groupm__groupcampaign__csvFile__name')
                elif cod == 1:
                    query = query.order_by('-groupm__groupcampaign__csvFile__name')
                elif cod == 2:
                    query = query.order_by('updated')
                elif cod == 4:
                    query = query.order_by('timestamp')
                elif cod == 5:
                    query = query.order_by('-timestamp')
                else:
                    query = query.order_by('-updated')
            except:
                query = query.order_by('-updated')
        else:
            query = CampaignProspect.objects.filter(pk__in=Subquery(query.values('pk')))
            query = query.order_by('-updated')

        #query = query.distinct('groupm__groupcampaign').order_by('groupm__groupcampaign','-timestamp')
        results = self.paginate_queryset(query, request, view=self)
        results = [GroupCampaign.objects.get(id=ii.groupm.groupcampaign.id) for ii in results]

        serializer = CampaignGroupBriefSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


import pandas as pd
from uuid import uuid1
class CampaignAllBriefView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignProspect.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignProspect.objects.filter(campaign__user=user)

        filter_ = request.GET.get('filter','')

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(uniqueIdentity__icontains=filter_) | query.filter(campaign__name__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(isMailedOpend=True)
                if 3 in category:
                    query = query.filter(isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(isCtaClicked=True)
                if 5 in category:
                    query = query.filter(isCollateral=True)
            except:
                pass
            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)


        query = query.distinct('campaign').order_by('campaign','-updated')

        isDownload = request.GET.get('download','')
        if isDownload:
            filePath = os.path.join(settings.MEDIA_ROOT,'dashboard/ongoing/')
            os.makedirs(filePath,exist_ok=True)
            try:
                fileName = str(MainCampaign.objects.filter(user=user).order_by('id').first().id)+'.csv'
            except:
                fileName = str(uuid1()) + '.csv'
            filePath += fileName
            results = [MainCampaign.objects.get(id=ii.campaign.id) for ii in query]
            allData = CampaignAllBriefSerializer(results, many=True,context={'request': request}).data
            df = pd.DataFrame(allData)
            df.to_csv(filePath,index=False)
            return Response({'url': f'{settings.MEDIA_URL}dashboard/ongoing/{fileName}'},status=status.HTTP_200_OK)
        
        order = request.GET.get('order','')
        if order:
            query = CampaignProspect.objects.filter(pk__in=Subquery(query.values('pk')))
            try:
                cod = int(order)
                if cod == 0:
                    query = query.order_by('campaign__name')
                elif cod == 1:
                    query = query.order_by('-campaign__name')
                elif cod == 2:
                    query = query.order_by('updated')
                elif cod == 4:
                    query = query.order_by('timestamp')
                elif cod == 5:
                    query = query.order_by('-timestamp')
                else:
                    query = query.order_by('-updated')
            except:
                query = query.order_by('-updated')

        results = self.paginate_queryset(query, request, view=self)
        results = [MainCampaign.objects.get(id=ii.campaign.id) for ii in results]
        serializer = CampaignAllBriefSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class DashboardProspectView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        user = request.user

        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        filter_ = request.GET.get('filter','')

        query = CampaignProspect.objects.filter(campaign__user=user)
        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(campaign__pk__in=campagins.split('_'))
            except:
                pass

        if filter_:
            query = query.filter(uniqueIdentity__icontains=filter_)
        
        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(isMailedOpend=True)
                if 3 in category:
                    query = query.filter(isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(isCtaClicked=True)
                if 5 in category:
                    query = query.filter(isCollateral=True)
            except:
                pass

        prospectStatus = request.GET.get('prospectstatus','')
        if prospectStatus or prospectStatus == 0 or prospectStatus == '0':
            try:
                allP = [int(i) for i in prospectStatus.split('_')]
                query = query.filter(prospectStatus__in=allP)
            except:
                return Response({'prospectStatus': ['This Field is not Valid.']},status=status.HTTP_400_BAD_REQUEST)


        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        order = request.GET.get('order','')
        query1 = query.distinct('uniqueIdentity').order_by('uniqueIdentity')
        if order:
            query1 = CampaignProspect.objects.filter(pk__in=Subquery(query1.values('pk')))
            try:
                cod = int(order)
                if cod == 1:
                    query1 = query1.order_by('-uniqueIdentity')
                elif cod == 2:
                    query1 = query1.order_by('updated')
                elif cod == 3:
                    query1 = query1.order_by('-updated')
                elif cod == 4:
                    query1 = query1.order_by('timestamp')
                elif cod == 5:
                    query1 = query1.order_by('-timestamp')
                else:
                    query1 = query1.order_by('uniqueIdentity')
            except:
                query1 = query1.order_by('uniqueIdentity')


        results = self.paginate_queryset(query1, request, view=self)
        customData = []
        for ii in results:
            data = {'uniqueIdentity': ii.uniqueIdentity}
            tmpQ = query.filter(uniqueIdentity=ii.uniqueIdentity).order_by('-updated')
            data['campData'] = DashProspectSerializer(tmpQ,many=True).data
            data['prospectStatus'] = tmpQ.first().prospectStatus
            
            customData.append(data)
        #serializer = DashboardProspectSerializer(results, many=True,context={'request': request})
        return self.get_paginated_response({'data': customData,'totalCampaign': query.distinct('campaign__id').order_by().count(),'totalProspect': query.count()})


from django.db.models.functions import (
    TruncDate, TruncDay,TruncWeek, TruncMonth, TruncYear
    )

from django.db.models import Count

class CampaignMailOGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignEmailOpenedAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignEmailOpenedAnalytics.objects.filter(campaign__user=user)
            


        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass

        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        minDataLen = 9
        allVFT = ['daily','weekly','monthly','yearly']
        fetchType = request.GET.get('fetchtype','')
        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(weeks=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(months=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(years=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)


        return Response({"xData": xData,"yData": yData,'total': query.count()},status=status.HTTP_200_OK)



class CampaignMailOEmailGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        date = request.GET.get('date','')
        if not date:
            return Response({'date': ['This Field is Required.']},status=status.HTTP_400_BAD_REQUEST) 
        try:
            #parse Date'
            date = datetime.strptime(date,"%Y-%m-%d")
        except:
            return Response({'date': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
            
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignEmailOpenedAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignEmailOpenedAnalytics.objects.filter(campaign__user=user)
            
        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass


        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        fetchType = request.GET.get('fetchtype','')

        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")

        try:
            fixedDateEmail = nq.filter(
                xData__year=date.year,
                xData__month=date.month,
                xData__day=date.day
                ).first()['emails']
        except:
            fixedDateEmail = []
        return Response({"emails": fixedDateEmail,'date': date,'fetchType': fetchType},status=status.HTTP_200_OK)


class CampaignLinkOGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignOpenAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignOpenAnalytics.objects.filter(campaign__user=user)

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass

            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        minDataLen = 9
        allVFT = ['daily','weekly','monthly','yearly']
        fetchType = request.GET.get('fetchtype','')
        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(weeks=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(months=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(years=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)


        return Response({"xData": xData,"yData": yData,'total': query.count()},status=status.HTTP_200_OK)



class CampaignLinkOEmailGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        date = request.GET.get('date','')
        if not date:
            return Response({'date': ['This Field is Required.']},status=status.HTTP_400_BAD_REQUEST) 
        try:
            #parse Date'
            date = datetime.strptime(date,"%Y-%m-%d")
        except:
            return Response({'date': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
            
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignOpenAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignOpenAnalytics.objects.filter(campaign__user=user)

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass
            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        fetchType = request.GET.get('fetchtype','')

        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")

        try:
            fixedDateEmail = nq.filter(
                xData__year=date.year,
                xData__month=date.month,
                xData__day=date.day
                ).first()['emails']
        except:
            fixedDateEmail = []
        return Response({"emails": fixedDateEmail,'date': date,'fetchType': fetchType},status=status.HTTP_200_OK)




class CampaignVideoPGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except MainCampaign.DoesNotExist:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')

        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignVideoPlayedAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignVideoPlayedAnalytics.objects.filter(campaign__user=user)
        
        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass

            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

        minDataLen = 9
        allVFT = ['daily','weekly','monthly','yearly']
        fetchType = request.GET.get('fetchtype','')
        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(weeks=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(months=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(years=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            xData = nq.values_list('xData',flat=True)
            yData = nq.values_list('yData',flat=True)

            if len(xData)==0:
                xData = [datetime.now()]
                yData = [0]
            
            totalRemData = minDataLen-len(xData)
            if totalRemData>0:
                lastD = xData[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                xData = frmD+list(xData)
                yData = [0]*totalRemData+list(yData)


        return Response({"xData": xData,"yData": yData,'total': query.count()},status=status.HTTP_200_OK)


            
        # if dfrom:
        #     query = query.filter(timestamp__gte=dfrom)
        # if dto:
        #     query = query.filter(timestamp__lte=dto)


        # fetchType = request.GET.get('fetchtype','')
        # if fetchType == 'daily':
        #     nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        # elif fetchType == 'weekly':
        #     nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        # elif fetchType == 'monthly':
        #     nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        # elif fetchType == 'yearly':
        #     nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        # else:
        #     nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")

        # ## removal part
        # testN = randint(30,60)
        # curntD = datetime.now()-timedelta(days=testN)
        # sdate = date(curntD.year,curntD.month,curntD.day)
        # xData = [sdate+timedelta(days=x) for x in range(testN)]
        # yData = [randint(1,100) for i in range(testN)]
        # return Response({"xData": xData,"yData": yData,'total': testN},status=status.HTTP_200_OK)
        # #return Response({"xData": nq.values_list('xData',flat=True),"yData": nq.values_list('yData',flat=True),'total': query.count()},status=status.HTTP_200_OK)


class CampaignVideoPEmailGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        date = request.GET.get('date','')
        if not date:
            return Response({'date': ['This Field is Required.']},status=status.HTTP_400_BAD_REQUEST) 
        try:
            #parse Date'
            date = datetime.strptime(date,"%Y-%m-%d")
        except:
            return Response({'date': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
            
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                query =  CampaignVideoPlayedAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            query = CampaignVideoPlayedAnalytics.objects.filter(campaign__user=user)

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
            except:
                pass
            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)

       
        allVFT = ['daily','weekly','monthly','yearly']
        fetchType = request.GET.get('fetchtype','')
            
        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(emails=ArrayAgg('uniqueIdentity')).order_by("xData")

        try:
            fixedDateEmail = nq.filter(
                xData__year=date.year,
                xData__month=date.month,
                xData__day=date.day
                ).first()['emails']
        except:
            fixedDateEmail = []
        return Response({"emails": fixedDateEmail,'date': date,'fetchType': fetchType},status=status.HTTP_200_OK)




class CampaignEngOGraphView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')

        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if is_exist:
                totalSent = CampaignSentAnalytics.objects.filter(campaign=inst).count()
                query = CampaignOpenAnalytics.objects.filter(campaign=inst)
                query1 = CampaignVideoPlayedAnalytics.objects.filter(campaign=inst)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            totalSent = CampaignSentAnalytics.objects.filter(campaign__user=user).count()
            query = CampaignOpenAnalytics.objects.filter(campaign__user=user)
            query1 = CampaignVideoPlayedAnalytics.objects.filter(campaign__user=user)

        campagins = request.GET.get('campaigns','')
        if campagins:
            try:
                query = query.filter(cpros__campaign__pk__in=campagins.split('_'))
                query1 = query1.filter(cpros__campaign__pk__in=campagins.split('_'))
            except:
                pass

        category = request.GET.get('category','')
        if category:
            try:
                category = list(map(int,category.split('_')))
                
                if 1 in category:
                    query = query.filter(cpros__isMailedOpend=True)
                    query1 = query1.filter(cpros__isMailedOpend=True)
                if 3 in category:
                    query = query.filter(cpros__isVideoPlayed=True)
                    query1 = query1.filter(cpros__isVideoPlayed=True)
                if 4 in category:
                    query = query.filter(cpros__isCtaClicked=True)
                    query1 = query1.filter(cpros__isCtaClicked=True)
                if 5 in category:
                    query = query.filter(cpros__isCollateral=True)
                    query1 = query1.filter(cpros__isCollateral=True)
            except:
                pass

            
        if dfrom:
            query = query.filter(timestamp__gte=dfrom)
            query1 = query1.filter(timestamp__gte=dfrom)
        if dto:
            query = query.filter(timestamp__lte=dto)
            query = query.filter(timestamp__lte=dto)

        minDataLen = 9
        allVFT = ['daily','weekly','monthly','yearly']
        fetchType = request.GET.get('fetchtype','')
        if fetchType == 'daily':
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            nq1 = query1.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        elif fetchType == 'weekly':
            nq = query.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            nq1 = query1.annotate(xData=TruncWeek('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        elif fetchType == 'monthly':
            nq = query.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            nq1 = query1.annotate(xData=TruncMonth('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        elif fetchType == 'yearly':
            nq = query.annotate(xData=TruncYear('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            nq1 = query1.annotate(xData=TruncYear('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
        else:
            nq = query.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")
            nq1= query1.annotate(xData=TruncDay('timestamp')).values("xData").annotate(yData=Count('id')).order_by("xData")


        allOpD = list(nq.values_list('xData',flat=True))
        allViD = list(nq1.values_list('xData',flat=True))
        allOp = {}
        allVd = {}
        for ii in nq:
            allOp[ii['xData']] = ii['yData']
        for ii in nq1:
            allVd[ii['xData']] = ii['yData']

        allFD = sorted(set(allOpD + allViD))

        videoEng = []
        for ii in allFD:
            try:
                videoEng.append((allVd[ii]/totalSent)*100)
            except:
                videoEng.append(0)
        openEng = []
        for ii in allFD:
            try:
                openEng.append((allOp[ii]/totalSent)*100)
            except:
                openEng.append(0)

        if len(allFD)==0:
            allFD = [datetime.now()]
            videoEng = [0]
            openEng = [0]
        totalRemData = minDataLen-len(allFD)
        if totalRemData>0:
            if fetchType == 'daily':
                lastD = allFD[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(days=totalRemData-rmd))
                allFD = frmD+allFD
                videoEng = [0]*totalRemData+videoEng
                openEng = [0]*totalRemData+openEng
            elif fetchType == 'weekly':
                lastD = allFD[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-timedelta(weeks=totalRemData-rmd))
                allFD = frmD+allFD
                videoEng = [0]*totalRemData+videoEng
                openEng = [0]*totalRemData+openEng
            elif fetchType == 'monthly':
                lastD = allFD[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(months=totalRemData-rmd))
                allFD = frmD+allFD
                videoEng = [0]*totalRemData+videoEng
                openEng = [0]*totalRemData+openEng
            elif fetchType == 'yearly':
                lastD = allFD[0]
                frmD = []
                for rmd in range(totalRemData):
                    frmD.append(lastD-relativedelta(years=totalRemData-rmd))
                allFD = frmD+allFD
                videoEng = [0]*totalRemData+videoEng
                openEng = [0]*totalRemData+openEng

        return Response({"xData": allFD,"videoEng": videoEng,'openEng': openEng, 'total': totalSent},status=status.HTTP_200_OK)





from salesPage.serializers import SalesPageEditorSerializer


class CampaignCTACAnalyticsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        campagins = request.GET.get('campaigns','')
        category = request.GET.get('category','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if not is_exist:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)

            soloT = SoloCampaign.objects.filter(campaign=inst)
            groupT = GroupSingleCampaign.objects.filter(groupcampaign__campaign=inst)
            if soloT.count()>=1:
                salepageD = json.loads(soloT.first().salesPageData)
            elif groupT.count()>=1:
                salepageD = json.loads(groupT.first().salesPageData)
            else:
                salepageD = SalesPageEditorSerializer(inst.salespage,context={'request': request}).data
            allBt = {}
            for i in salepageD['buttonEditor']:
                if i['isDeleted'] == False:
                    for j in i['buttonData']:
                        if j['isDeleted'] == False:
                            allBt[j['id']] = {'name': j['name'],'totalClicked': 0}

            isZero = True
            for ii in allBt:
                query =  CampaignCtaClickedtAnalytics.objects.filter(campaign=inst,buttonId=ii)

                if category:
                    try:
                        category = list(map(int,category.split('_')))
                        
                        if 1 in category:
                            query = query.filter(cpros__isMailedOpend=True)
                        if 3 in category:
                            query = query.filter(cpros__isVideoPlayed=True)
                        if 4 in category:
                            query = query.filter(cpros__isCtaClicked=True)
                        if 5 in category:
                            query = query.filter(cpros__isCollateral=True)
                    except:
                        pass
                if dfrom:
                    query = query.filter(timestamp__gte=dfrom)
                if dto:
                    query = query.filter(timestamp__lte=dto)
                
                allBt[ii]['totalClicked'] = query.count()
            
            return Response(allBt.values(),status=status.HTTP_200_OK)
            
        else:
            tquery = MainCampaign.objects.filter(user=user)
            if campagins:
                try:
                    tquery = tquery.filter(pk__in=campagins.split('_'))
                except:
                    pass

            order = request.GET.get('order','')
            if order:
                try:
                    cod = int(order)
                    if cod == 0:
                        tquery = tquery.order_by('name')
                    elif cod == 1:
                        tquery = tquery.order_by('-name')
                    elif cod == 2:
                        tquery = tquery.order_by('updated')
                    elif cod == 4:
                        tquery = tquery.order_by('timestamp')
                    elif cod == 5:
                        tquery = tquery.order_by('-timestamp')
                    else:
                        tquery = tquery.order_by('-updated')
                except:
                    tquery = tquery.order_by('-updated')
            else:
                tquery = tquery.order_by('-updated')

            finalData = []
            for inst in tquery:
                soloT = SoloCampaign.objects.filter(campaign=inst)
                groupT = GroupSingleCampaign.objects.filter(groupcampaign__campaign=inst)
                if soloT.count()>=1:
                    salepageD = json.loads(soloT.first().salesPageData)
                elif groupT.count()>=1:
                    salepageD = json.loads(groupT.first().salesPageData)
                else:
                    salepageD = SalesPageEditorSerializer(inst.salespage,context={'request': request}).data
                allBt = {}
                for i in salepageD['buttonEditor']:
                    if i['isDeleted'] == False:
                        for j in i['buttonData']:
                            if j['isDeleted'] == False:
                                allBt[j['id']] = {'name': j['name'],'totalClicked': 0}
                isZero = True
                for ii in allBt:
                    query = CampaignCtaClickedtAnalytics.objects.filter(campaign=inst,buttonId=ii)
                    if category:
                        try:
                            category = list(map(int,category.split('_')))
                            
                            if 1 in category:
                                query = query.filter(cpros__isMailedOpend=True)
                            if 3 in category:
                                query = query.filter(cpros__isVideoPlayed=True)
                            if 4 in category:
                                query = query.filter(cpros__isCtaClicked=True)
                            if 5 in category:
                                query = query.filter(cpros__isCollateral=True)
                        except:
                            pass
                    if dfrom:
                        query = query.filter(timestamp__gte=dfrom)
                    if dto:
                        query = query.filter(timestamp__lte=dto)
                    tttCount = query.count()
                    allBt[ii]['totalClicked'] = tttCount
                    if tttCount>0:
                        isZero = False
                if not isZero:     
                    finalData.append({'data': allBt.values(),'campaign_name': inst.name})
                
            return Response(finalData,status=status.HTTP_200_OK)





class CampaignCollateralAnalyticsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        campaign = request.GET.get('campaign','')
        campagins = request.GET.get('campaigns','')
        category = request.GET.get('category','')
        dfrom = request.GET.get('from','')
        dto = request.GET.get('to','')
        if dfrom:
            try:
                dfrom = datetime.strptime(dfrom,"%Y-%m-%d")
            except:
                return Response({'from': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)
        if dto:
            try:
                dto = datetime.strptime(dto,"%Y-%m-%d")
            except:
                return Response({'to': ['This Field is not Valid ("%Y-%m-%d").']},status=status.HTTP_400_BAD_REQUEST)

        if campaign:
            is_exist,inst = self.get_object(campaign,user)
            if not is_exist:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)

            soloT = SoloCampaign.objects.filter(campaign=inst)
            groupT = GroupSingleCampaign.objects.filter(groupcampaign__campaign=inst)
            if soloT.count()>=1:
                salepageD = json.loads(soloT.first().salesPageData)
            elif groupT.count()>=1:
                salepageD = json.loads(groupT.first().salesPageData)
            else:
                salepageD = SalesPageEditorSerializer(inst.salespage,context={'request': request}).data
            allBt = {}
            for i in salepageD['crouselEditor']:
                if i['isDeleted'] == False:
                    for j in i['crouselData']:
                        allBt[j['id']] = {'name': j['name'],'totalClicked': 0,'media_thumbnail': j['media_thumbnail']}

            for ii in allBt:
                query =  CampaignCollateralClickedtAnalytics.objects.filter(campaign=inst,fileId=ii)
                if category:
                    try:
                        category = list(map(int,category.split('_')))
                        if 1 in category:
                            query = query.filter(cpros__isMailedOpend=True)
                        if 3 in category:
                            query = query.filter(cpros__isVideoPlayed=True)
                        if 4 in category:
                            query = query.filter(cpros__isCtaClicked=True)
                        if 5 in category:
                            query = query.filter(cpros__isCollateral=True)
                    except:
                        pass
                if dfrom:
                    query = query.filter(timestamp__gte=dfrom)
                if dto:
                    query = query.filter(timestamp__lte=dto)
                allBt[ii]['totalClicked'] = query.count()
            
            return Response(allBt.values(),status=status.HTTP_200_OK)
            
        else:
            tquery = MainCampaign.objects.filter(user=user)
            if campagins:
                try:
                    tquery = tquery.filter(pk__in=campagins.split('_'))
                except:
                    pass
            
            order = request.GET.get('order','')
            if order:
                try:
                    cod = int(order)
                    if cod == 0:
                        tquery = tquery.order_by('name')
                    elif cod == 1:
                        tquery = tquery.order_by('-name')
                    elif cod == 2:
                        tquery = tquery.order_by('updated')
                    elif cod == 4:
                        tquery = tquery.order_by('timestamp')
                    elif cod == 5:
                        tquery = tquery.order_by('-timestamp')
                    else:
                        tquery = tquery.order_by('-updated')
                except:
                    tquery = tquery.order_by('-updated')
            else:
                tquery = tquery.order_by('-updated')

            finalData = []
            for inst in tquery:
                soloT = SoloCampaign.objects.filter(campaign=inst)
                groupT = GroupSingleCampaign.objects.filter(groupcampaign__campaign=inst)
                if soloT.count()>=1:
                    salepageD = json.loads(soloT.first().salesPageData)
                elif groupT.count()>=1:
                    salepageD = json.loads(groupT.first().salesPageData)
                else:
                    salepageD = SalesPageEditorSerializer(inst.salespage,context={'request': request}).data
                allBt = {}
                for i in salepageD['crouselEditor']:
                    if i['isDeleted'] == False:
                        for j in i['crouselData']:
                            allBt[j['id']] = {'name': j['name'],'totalClicked': 0,'media_thumbnail': j['media_thumbnail']}
                isZero = True
                for ii in allBt:
                    query = CampaignCollateralClickedtAnalytics.objects.filter(campaign=inst,fileId=ii)
                    if category:
                        try:
                            category = list(map(int,category.split('_')))
                            
                            if 1 in category:
                                query = query.filter(cpros__isMailedOpend=True)
                            if 3 in category:
                                query = query.filter(cpros__isVideoPlayed=True)
                            if 4 in category:
                                query = query.filter(cpros__isCtaClicked=True)
                            if 5 in category:
                                query = query.filter(cpros__isCollateral=True)
                        except:
                            pass
                    if dfrom:
                        query = query.filter(timestamp__gte=dfrom)
                    if dto:
                        query = query.filter(timestamp__lte=dto)
                    tttCount = query.count()
                    allBt[ii]['totalClicked'] = tttCount
                    if tttCount>0:
                        isZero = False
                if not isZero:     
                    finalData.append({'data': allBt.values(),'campaign_name': inst.name})
            return Response(finalData,status=status.HTTP_200_OK)
