from django.conf import settings
from rest_framework import serializers, status

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q, query_utils
import os,re
from userlibrary.models import FileUpload
from userlibrary.serializers import FileUploadSerializer
import json
from threading import Thread

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


import logging
import traceback
from uuid import UUID,uuid4

from utils.customValidators import isValidUrl

from campaign.models import (
    EmailClient, GroupCampaign, MainCampaign,SoloCampaign,
    GroupSingleCampaign
)

import pandas as pd
from campaign.models import MAIL_CLIENT_CHOICES

from campaign.serializers import (
    EmailClientSerializer, MainCampaignCreateSerializer,MainCampaignDetailsSerializer,
    SoloCampaignSerializer,GroupCampaignSerializer,GroupSingleCampaignSerializer,
    GroupSingleCampaignDownloadSerializer,MainCampaignMinSerializer,
    MainCampaignLinkedSerializer
)

from salesPage.models import (
    SalesPageDetails
)
from newVideoCreator import models as newVideoCreatorModels
from urlShortner import models as urlShortnerModels
from salesPage.serializers import (
    SalesPageEditorSerializer,SalesPageDetailsSerializer
)

from aiQueueManager.models import (
    VideoRenderMultipleScene,AiTask,GeneratedFinalVideo
)
from aiQueueManager.serializers import GenerateFinalVideoSerializer

from salesPage.models import SalesPageEditor
from subscriptions.models import VideoCreditUsage
from math import ceil
from videoThumbnail.serializers import MainThumbnailListSerializer
from newVideoCreator import serializers as newVideoCreatorSerializers
from videoThumbnail.models import MainThumbnail

logger = logging.getLogger(__name__)


class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50


class CampaignListMinView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainCampaignMinSerializer

    def get(self, request, format=None):

        queryset = MainCampaign.objects.filter(user=request.user)
    
        serializer = self.serializer_class(queryset, many=True,context={'request': request})
        return Response({'results': serializer.data},status=status.HTTP_200_OK)


class SalesPageLinkedCampaignView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainCampaignLinkedSerializer

    def get(self, request,pk, format=None):

        try:
            inst = SalesPageEditor.objects.get(id=pk)
        except:
            return Response({'message': "Video Id Not Valid."},status=status.HTTP_400_BAD_REQUEST)
        queryset = MainCampaign.objects.filter(user=request.user,salespage=inst).order_by('-updated')
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


class VideoLinkedCampaignView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainCampaignLinkedSerializer

    def get(self, request,pk, format=None):

        try:
            inst = VideoRenderMultipleScene.objects.get(id=pk)
        except:
            return Response({'message': "Video Id Not Valid."},status=status.HTTP_400_BAD_REQUEST)
        queryset = MainCampaign.objects.filter(user=request.user,video=inst).order_by('-updated')
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class CampaignListView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainCampaignCreateSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','')
        filter = data.get('filter','')

        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        queryset = MainCampaign.objects.filter(user=request.user)
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(Q(tags__icontains=filter) | Q(name__icontains=filter))

        if isOrder != None:
            queryset = queryset.order_by(isOrder)
    
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)


    def post(self, request, format=None):
        user = request.user
        data = request.data
        errors = {'video': [],'salespage': []}
        isError = False

        videoId = data.get('video','')
        salePageId = data.get('salespage','')
        name = data.get('name','')

        if videoId=='':
            errors['video'].append("This field is required.")
            isError=True
        else:
            try:
                videoId = int(videoId)
                video = VideoRenderMultipleScene.objects.get(user=user,id=videoId)
                if video.generateStatus.status != 1:
                    errors['video'].append("Video is Not Generated.")
                    isError=True
            except:
                errors['video'].append("This field is not Valid.")
                isError=True
        if salePageId=='':
            errors['salespage'].append("This field is required.")
            isError=True
        else:
            try:
                salePageId = int(salePageId)
                salespage = SalesPageEditor.objects.get(user=user,id=salePageId)
                if salespage.isPublish==False:
                    errors['salespage'].append("SalesPage Must be Publish.")
                    isError=True
            except:
                errors['salespage'].append("This field is not Valid.")
                isError=True
        if isError:
            return Response(errors,status=status.HTTP_400_BAD_REQUEST)

        else:
            if name=='':
                lC = MainCampaign.objects.filter(user=user).last()
                if lC:
                    name = f'Campaign {lC.id}'
                else:
                    name = 'Campaign 1'
            campaign = MainCampaign.objects.create(user=user,name=name,video=video,salespage=salespage,selectedThumbnail=video.selectedThumbnail)

            campaign.save()
            campaign.setThumbnail()
        
            serializer = self.serializer_class(campaign,context={'request': request})
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)

from django.core.validators import validate_email
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string
from aiQueueManager.serializers import VideoDetailsSerializer
from datetime import datetime
from campaignAnalytics.models import CampaignGroupAnalytics, CampaignProspect

def sendGroupCampaignEmail(singleGroupInst):
    try:
        groupInst = singleGroupInst.groupcampaign

        inst_ = CampaignGroupAnalytics(campaign=singleGroupInst,command=0)
        inst_.save()

        inst = groupInst.campaign
        validate_email(singleGroupInst.uniqueIdentity)
        template_prefix = 'campaign/campaign_group_email'
        open('/home/govind/sendgroupEmail.txt','a').write(f"{datetime.now()} ==> {singleGroupInst.uniqueIdentity} Sending\n")

        subject_file = '%s_subject.txt' % template_prefix
        txt_file = '%s.txt' % template_prefix
        html_file = '%s.html' % template_prefix

        template_ctxt = {
            'campaign_name': inst.name,
            'sender_email': inst.user.email,
            'name': singleGroupInst.uniqueIdentity.split('@')[0],
            'thumbnail_url': settings.BASE_URL + f"/campaign/thumbnail/?campaign={groupInst.id}&uid={singleGroupInst.uniqueIdentity}",
            'campaign_url': settings.FRONTEND_URL + '/preview/' + str(groupInst.id)+f'/?email={singleGroupInst.uniqueIdentity}'
        }
        
        from_email = settings.EMAIL_FROM
        bcc_email = settings.EMAIL_BCC

        subject = render_to_string(subject_file,template_ctxt).strip()
        text_content = render_to_string(txt_file, template_ctxt)
        html_content = render_to_string(html_file, template_ctxt)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [singleGroupInst.uniqueIdentity],
                                    bcc=[bcc_email])
        msg.attach_alternative(html_content, 'text/html')
        if singleGroupInst.uniqueIdentity.lower() not in ['kiran@ut-ec.co.jp','kobayashi@ut-ec.co.jp']:
            if singleGroupInst.uniqueIdentity.lower().split('@')[-1] == 'gmail.com':
                #msg.send()
                pass
        open('/home/govind/sendgroupEmail.txt','a').write(f"{datetime.now()} ==> {singleGroupInst.uniqueIdentity} Send\n")
        return True
    except Exception as e:
        open('/home/govind/sendgroupEmail.txt','a').write(f"{datetime.now()} ==> {singleGroupInst.uniqueIdentity} Failed {e}\n")
        return False

class CampaignTestEmailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except MainCampaign.DoesNotExist:
            return (False,'')

    def post(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            email = request.data.get('email')
            if email:
                try:
                    ## validate email
                    validate_email(email)
                except:
                    content = {'email': ['This Field is Not Valid']}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
                videoObj = VideoDetailsSerializer(inst.video,context={'request': request}).data
                template_prefix = 'campaign/campaign_test_email'

                subject_file = '%s_subject.txt' % template_prefix
                txt_file = '%s.txt' % template_prefix
                html_file = '%s.html' % template_prefix

                template_ctxt = {
                    'campaign_name': inst.name,
                    'sender_email': request.user.email,
                    'name': email.split('@')[0],
                    'thumbnail_url': videoObj['thumbnailImage'],
                    'campaign_url': settings.FRONTEND_URL + '/preview/' + str(inst.id)+'/?type=campaign_test'
                }
                
                from_email = settings.EMAIL_FROM
                bcc_email = settings.EMAIL_BCC

                subject = render_to_string(subject_file,template_ctxt).strip()
                text_content = render_to_string(txt_file, template_ctxt)
                html_content = render_to_string(html_file, template_ctxt)
                msg = EmailMultiAlternatives(subject, text_content, from_email, [email],
                                            bcc=[bcc_email])
                msg.attach_alternative(html_content, 'text/html')
                msg.send()
                return Response({'status': 'ok'},status=status.HTTP_200_OK)
            else:
                content = {'email': ['This Field is Not Required']}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class CampaignDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MainCampaignDetailsSerializer

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except MainCampaign.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            sData = self.serializer_class(inst,context={'request': request}).data
            if inst.video.generateStatus:
                sData['video']['url'] = f'{request.scheme}://{request.get_host()}{inst.video.generateStatus.video.url}'
                sData['video']['thumbnailImage'] = f'{request.scheme}://{request.get_host()}{inst.video.generateStatus.thumbnailImage.url}'
            
            sData['mergeTag'] = inst.getUsedMergeTag()
            content = {'result': sData}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        
    def put(self, request,pk, format=None):
        user = request.user
        data = request.data.copy()
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            errors = {'video': [],'salespage': []}
            isError = False

            videoId = data.get('video','')
            salePageId = data.get('salespage','')

            if videoId!='':
                try:
                    videoId = int(videoId)
                    if videoId != inst.video.id:
                        errors['video'].append("Video Cannot Be Changed.")
                        isError=True
                    else:
                        video = VideoRenderMultipleScene.objects.get(user=user,id=videoId)
                        if video.generateStatus.status != 1:
                            errors['video'].append("Video is Not Generated.")
                            isError=True
                except:
                    errors['video'].append("This field is not Valid.")
                    isError=True
            if salePageId!='':
                try:
                    salePageId = int(salePageId)
                    if salePageId != inst.salespage.id:
                        errors['salespage'].append("SalesPage Cannot Be Changed.")
                        isError=True
                    salespage = SalesPageEditor.objects.get(user=user,id=salePageId)
                except:
                    errors['salespage'].append("This field is not Valid.")
                    isError=True

            thumbnailId = data.pop('thumbnailId',None)
            if thumbnailId:
                try:
                    mainThumbnailInst = MainThumbnail.objects.get(id = int(thumbnailId))
                    if mainThumbnailInst.category!=1:
                        if mainThumbnailInst.user.id != user.id:
                            content = {'thumbnailId': ['This Field is Not Valid.']}
                            return Response(content,status=status.HTTP_400_BAD_REQUEST)
                    inst.selectedThumbnail = mainThumbnailInst
                    inst.save()
                    inst.setThumbnail()
                    return Response({"mergeTag": inst.getUsedMergeTag()},status=status.HTTP_200_OK)
                except Exception as e:
                    logger.error(str(traceback.format_exc()))
                    content = {'thumbnailId': ['This Field is Not Valid.']}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)

            if isError:
                return Response(errors,status=status.HTTP_400_BAD_REQUEST)

            serializer = MainCampaignCreateSerializer(inst, data=data,partial=True,context={'request': request})
            if serializer.is_valid():
                inst = serializer.save()
                
                ## set thubmnail
                inst.setThumbnail()
                return Response(serializer.data)
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
            inst.delete()
            content = {'name': name,'isError': False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': False}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


def updateSalesPageData(finst,mtagValue):
                
    for ind,ii in enumerate(finst['textEditor']):
        text = ii['content']
        for ii in mtagValue:
            text = text.replace(ii,mtagValue[ii])
        finst['textEditor'][ind]['content'] = text

    return finst
       

from bs4 import BeautifulSoup
import urllib
class SoloCampignDetailsView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = SoloCampaignSerializer

    def get_campaign(self,pk):
        try:
            return (True,MainCampaign.objects.get(pk=pk))
        except:
            return (False,'')

    def get_solo_object(self, pk):
        try:
            return (True,SoloCampaign.objects.get(pk=pk))
        except:
            return (False,'')


    def get_short_url_obj(self,slug):
        try:
            _inst = urlShortnerModels.CampaignUrlShortner.objects.get(slug=slug)
            if _inst._type == 2 or _inst._type == 3:
                return (True,_inst)
        except:
            pass
        return (False,None)

    def get_video_generate(self,uid):
        try:
            return (True,newVideoCreatorModels.MainVideoGenerate.objects.get(id=uid))
        except:
            return (False,'')

    def get_group_handler(self,uid):
        try:
            return (True,newVideoCreatorModels.GroupHandler.objects.get(id=uid))
        except:
            return (False,"")
      

    def get_video_generate_batch(self,uid,uniqueIdentity=False):
        is_exist,_inst = self.get_group_handler(uid)
        if is_exist:
            if uniqueIdentity:
                try:
                    inst = newVideoCreatorModels.MainVideoGenerate.objects.get(groupHandlerTracker=_inst,uniqueIdentity__iexact=uniqueIdentity)
                    return (2,inst)
                except:
                    return (True,_inst)
            return (True,_inst)
        return (False,None)


    def get_group_object(self,gpid,uid):
        try:
            gpInst = GroupCampaign.objects.get(id=gpid)
            try:
                gpSinst = GroupSingleCampaign.objects.get(uniqueIdentity=uid,groupcampaign=gpInst)
                return (True,gpInst,gpSinst)
            except:
                return (False,'','')
        except:
            return (False,'','')

    def get(self, request,pk, format=None):
        uid = request.GET.get('uid','')
        _tagValue = urllib.parse.unquote(request.GET.get('tag_value',''))
        
        type_ = 1
        salesPageDetails = None
        finst = None
        is_exist = None
        salesPageDetails = {'salesPage': None,'favicon': {'media_file': "https://salespage.autogenerate.ai/autogenFavicon.svg"}}


        is_exist,_shortUrlObj = self.get_short_url_obj(pk)
        if is_exist:
            if _shortUrlObj._type == 2:
                # NEWVIDEOCREATOR_MAINVIDEOGENERATE
                type_ = 4
                is_exist,inst = self.get_video_generate(_shortUrlObj.mainId)
            elif _shortUrlObj._type == 3:
                # NEWVIDEOCREATOR_GROUPHANDLER
                type_ = 5
                is_exist,inst = self.get_video_generate_batch(_shortUrlObj.mainId,uniqueIdentity=uid)
                if is_exist == 2:
                    type_ = 4
        else:
            if uid:
                if uid=='campaign_test':
                    type_ = 3
                    is_exist,inst = self.get_campaign(pk)
                    if is_exist:
                        salesPageDetails = SalesPageDetailsSerializer(SalesPageDetails.objects.get(salesPage=inst.salespage),context={'request': request}).data
                elif uid == 'video_creator' or uid == 'nvc':
                    type_ = 4
                    is_exist,inst = self.get_video_generate(pk)
                elif uid[-9:] == '__batch__':
                    # new video creator batch mail
                    _uniqueIdentity = uid[:-9]
                    if _uniqueIdentity=='campaign_test':
                        type_ = 5
                        is_exist,inst = self.get_video_generate_batch(pk)
                    else:
                        type_ = 4
                        is_exist,inst = self.get_video_generate_batch(pk,uniqueIdentity=_uniqueIdentity)
                else:
                    type_ = 2
                    is_exist,inst,gpsinst = self.get_group_object(pk,uid)
                    if is_exist:
                        salesPageDetails = SalesPageDetailsSerializer(SalesPageDetails.objects.get(salesPage=inst.campaign.salespage),context={'request': request}).data
            else:
                is_exist,inst = self.get_solo_object(pk)
                if is_exist:
                    salesPageDetails = SalesPageDetailsSerializer(SalesPageDetails.objects.get(salesPage=inst.campaign.salespage),context={'request': request}).data

        user = request.user
        if is_exist:
            salesPageDetails.pop('salesPage')
            if salesPageDetails['favicon']:
                salesPageDetails['favicon'] = salesPageDetails['favicon']['media_file']
            if type_==1:
                finst = json.loads(inst.salesPageData)
                tempInst = GenerateFinalVideoSerializer(inst.genVideo,context={'request': request}).data

            # new Video Creator
            elif type_==4:
                if inst.generationType==0:
                    finst = SalesPageEditorSerializer(inst.videoCreator.sharingPage,context={'request': request}).data
                    tempInst = newVideoCreatorSerializers.MainVideoGenerateForCampaignSerializer(inst,context={'request': request}).data

                    # realtime group code
                    _parseMTag = {}
                    _salesMTag = {}
                    _reg = r'({{.*?\}})_(text|url|email)=((?:(?!&{{).)*)'
                    for _t in re.findall(_reg,_tagValue):
                        _parseMTag[f"{_t[0]}_{_t[1]}"] = _t[2]
                        if _t[1] == 'text':
                            _salesMTag[_t[0]] = _t[2]

                    if len(_parseMTag):
                        finst = updateSalesPageData(finst,_salesMTag)
                        # thumbnail
                        _thumbnailRTData = inst.videoCreator.thumbnailInst.generateImageWithMTagRealtime(_parseMTag,creditType="PERSONALIZE_THUMBNAIL")
                        tempInst["thumbnailImage"] = _thumbnailRTData[1]

                        #set oe:image
                        if os.path.isfile(_thumbnailRTData[0].replace('.jpeg','_play.jpeg')):
                            salesPageDetails['oeImage'] = tempInst["thumbnailImage"].replace('.jpeg','_play.jpeg')
                        else:
                            salesPageDetails['oeImage'] = tempInst["thumbnailImage"]

                    else:
                        tempInst["thumbnailImage"] = tempInst.pop("thumbnail")

                        #set oe:image
                        salesPageDetails['oeImage'] = tempInst["thumbnailImage"]
                        if inst.videoCreator.thumbnailInst:
                            if inst.videoCreator.thumbnailInst.thumbnail and os.path.isfile(inst.videoCreator.thumbnailInst.thumbnail.path.replace('.jpeg','_play.jpeg')):
                                salesPageDetails['oeImage'] = tempInst["thumbnailImage"].replace('.jpeg','_play.jpeg') 

                else:
                    finst = json.loads(inst.sharingPageData)
                    tempInst = newVideoCreatorSerializers.MainVideoGenerateForCampaignSerializer(inst,context={'request': request}).data
                    tempInst["thumbnailImage"] = tempInst.pop("thumbnail")

                    #set oe:image
                    if inst.thumbnail and os.path.isfile(inst.thumbnail.path.replace('.jpeg','_play.jpeg')):
                        salesPageDetails['oeImage'] = tempInst["thumbnailImage"].replace('.jpeg','_play.jpeg')
                    else:
                        salesPageDetails['oeImage'] = tempInst["thumbnailImage"]

            elif type_==5:
                finst = json.loads(inst.sharingPageData)
                tempInst = newVideoCreatorSerializers.BatchVideoGenerateForCampaignSerializer(inst,context={'request': request}).data

                #set oe:image
                if inst.thumbnailInst.thumbnail and os.path.isfile(inst.thumbnailInst.thumbnail.path.replace('.jpeg','_play.jpeg')):
                    salesPageDetails['oeImage'] = tempInst["thumbnailImage"].replace('.jpeg','_play.jpeg')
                else:
                    salesPageDetails['oeImage'] = tempInst["thumbnailImage"]
                
            elif type_== 3:
                finst = SalesPageEditorSerializer(inst.salespage,context={'request': request}).data
                tempInst = GenerateFinalVideoSerializer(inst.video.generateStatus,context={'request': request}).data
                _thumbInst = MainThumbnailListSerializer(inst.selectedThumbnail,context={'request': request}).data
                tempInst["thumbnailImage"] = _thumbInst["thumbnailImage"]
            else:
                finst = json.loads(gpsinst.salesPageData)
                tempInst = GenerateFinalVideoSerializer(gpsinst.genVideo,context={'request': request}).data

           

            finst['videoEditor'][0]['src'] = tempInst['video']
            finst['videoEditor'][0]['thumbnail'] = tempInst['thumbnailImage']

            # set oe:Image
            if type_ != 4 and type_!=5:
                salesPageDetails['oeImage'] = tempInst['thumbnailImage']

            salesPageDetails['oeTitle'] = ''
            for ind,ii in enumerate(finst['textEditor']):
                try:
                    salesPageDetails['oeTitle'] = BeautifulSoup(ii['content'],'html.parser').text
                    break
                except:
                    break
            finst['pageDetails'] = salesPageDetails
            content = {'result': finst}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


from django.utils import timezone


class SoloCampignView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SoloCampaignSerializer

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except MainCampaign.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            queryset = SoloCampaign.objects.filter(campaign=inst).order_by('-timestamp')
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self,request,pk,format=None):
        user = request.user
        data = request.data
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if (user.totalVideoCredit - user.usedVideoCredit)<=0:
                content = {'detail': 'Not Enough Video Credit'}
                return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            if user.subs_end:
                if timezone.now()>user.subs_end:
                    content = {'detail': 'Subscriptions End'}
                    return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            else:
                content = {'detail': 'Subscriptions End'}
                return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)

            allTag = inst.getUsedMergeTag()
            mergeTag = {}
            for mtag in allTag:
                mergeTag[mtag["name"]] = mtag["value"]

            senderName = data.get('{{senderName}}','')
            mergeTag = sorted(mergeTag)
            reqMT = {ii: [] for ii in mergeTag}
            fData = {ii: [] for ii in mergeTag}
            isError = False
            for ii in mergeTag:
                if ii not in data:
                    reqMT[ii].append('This field is Required.')
                    isError=True
                else:
                    if ii in ["{{WebsiteScreenshot}}","{{Logo}}","{{Website}}","{{Profile}}"]:
                        ## validate url
                        isValid,url = isValidUrl(data[ii])
                        if isValid:
                            fData[ii] = url
                        else:
                            reqMT[ii].append('This field is not Valid. Must be type of URL.')
                            isError = True
                    else:
                        fData[ii] = data[ii]



            if not senderName:
                reqMT['{{senderName}}']= ['This field is Required.']
                isError = True
            if isError:
                content = {'errors': reqMT}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)

            else:
                stinst,ct = SoloCampaign.objects.get_or_create(campaign=inst,data=json.dumps(fData),uniqueIdentity=senderName)
                if ct:
                    allSceneInst = inst.video.singleScene.all()
                    isVideoBg = False
                    texts = []
                    for tinst in allSceneInst:
                        texts.append(tinst.getCustomParsedText(fData))
                        if tinst.isSnapshotMergeTag and tinst.bgVideoType==5:
                            isVideoBg = True


                    getUniqueData =inst.video.getUniqueDataM(texts)

                    if isVideoBg:
                        getUniqueData = json.loads(getUniqueData)
                        getUniqueData['{{WebsiteScreenshot}}'] = fData["{{WebsiteScreenshot}}"]
                        getUniqueData = json.dumps(getUniqueData)

                    finalGInstQ = GeneratedFinalVideo.objects.filter(multipleScene=inst.video,output=getUniqueData,status=1)
                    created = False
                    if finalGInstQ.count()>=1:
                        finalGInst = finalGInstQ.first()
                        finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=f"{senderName}_{inst.video.name}",isDefault=3,multipleScene=inst.video,output=getUniqueData,video=finalGInst.video,status=1,soloCampaign=stinst)
                        if created:
                            finalGInst.onVideoComplete()
                    else:
                        finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=f"{senderName}_{inst.video.name}",isDefault=3,multipleScene=inst.video,output=getUniqueData,soloCampaign=stinst)

                    if created:
                        finalGInst.thumbnailImage = inst.selectedThumbnail.thumbnailImage
                        finalGInst.save()
                    
                    finalGInst.setThumbnail(playButton=True)



                    stinst.genVideo = finalGInst

                    finst = SalesPageEditorSerializer(stinst.campaign.salespage,context={'request': request}).data
                    mergeVData = []
                    for ii in inst.getUsedMergeTag(onlyVideo=False):
                        mergeVData.append([ii['name'],fData[ii['name']]])

                    for ind,ii in enumerate(finst['textEditor']):
                        text = ii['content']
                        for ii in mergeVData:
                            text = text.replace(ii[0],ii[1])
                        finst['textEditor'][ind]['content'] = text
                    stinst.salesPageData = json.dumps(finst)
                    stinst.save()
                    

                serializers = self.serializer_class(stinst,context={'request': request})
                content = {'result': serializers.data }
                return Response(content,status=status.HTTP_201_CREATED)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class GroupSingleCampignView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GroupSingleCampaignSerializer

    def get_object(self, pk,user):
        try:
            return (True,GroupCampaign.objects.get(pk=pk,campaign__user=user))
        except GroupCampaign.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        isDownload = request.GET.get('download','')
        isQuery = request.GET.get('filter','')
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if isQuery:
                queryset = GroupSingleCampaign.objects.filter(groupcampaign=inst,data__icontains=isQuery)
            else:
                queryset = GroupSingleCampaign.objects.filter(groupcampaign=inst)

            if isDownload:
                filePath = os.path.join(settings.MEDIA_ROOT,'campaign/group/')
                os.makedirs(filePath,exist_ok=True)
                filePath += str(inst.id)+'.csv'
                if not (inst.isGenerated and os.path.isfile(filePath)):
                    allData = GroupSingleCampaignDownloadSerializer(queryset, many=True,context={'request': request}).data
                    df = pd.DataFrame(allData)
                    df.to_csv(filePath,index=False)
                return Response({'url': f'{settings.MEDIA_URL}campaign/group/{str(inst.id)}.csv'},status=status.HTTP_200_OK)
            else:
                results = self.paginate_queryset(queryset, request, view=self)
                serializer = self.serializer_class(results, many=True,context={'request': request})
                reqD = serializer.data
                headers = list(json.loads(inst.mergeTagMap).keys())
                headers=headers+['campaignLink']
                return self.get_paginated_response({'table': reqD,'headers': headers})
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)        


class GroupCampignView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GroupCampaignSerializer

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except MainCampaign.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            queryset = GroupCampaign.objects.filter(campaign=inst,isValidated=False).order_by('-timestamp')
            results = self.paginate_queryset(queryset, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


from django.core.validators import validate_email,URLValidator

class GroupCampignValidateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GroupCampaignSerializer
    urlValidate = URLValidator()
    allClientIndex = [i[0] for i in MAIL_CLIENT_CHOICES]

    def get_object(self, pk,user):
        try:
            return (True,MainCampaign.objects.get(pk=pk,user=user))
        except MainCampaign.DoesNotExist:
            return (False,'')

    def post(self,request,pk,format=None):
        user = request.user
        data = request.data
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if (user.totalVideoCredit - user.usedVideoCredit)<=0:
                content = {"error2": { 1: { "message" :"Not Enough Video Credit."}}}
                return Response(content,status=status.HTTP_200_OK)
                # content = {'detail': 'Not Enough Video Credit'}
                # return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            if user.subs_end:
                if timezone.now()>user.subs_end:
                    content = {"error2": { 1: { "message" :"Subscription Ended."}}}
                    return Response(content,status=status.HTTP_200_OK)
                    # content = {'detail': 'Subscriptions End'}
                    # return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            else:
                content = {"error2": { 1: { "message" :"Subscription Ended."}}}
                return Response(content,status=status.HTTP_200_OK)
                

            allTag = inst.getUsedMergeTag()
            mergeVData = {}
            for mtag in allTag:
                mergeVData[mtag["name"]] = mtag["value"]
            
            mergeTag = ['{{GroupEmailId}}'] + sorted(mergeVData)

            ## mail Client
            mailClient = data.get('mailClient')
            if not mailClient and mailClient != 0:
                content = {"error2": { 1: { "message" :"mailClient Field is Required."}}}
                return Response(content,status=status.HTTP_200_OK)
            if mailClient not in self.allClientIndex:
                content = {"error2": { 1: { "message" :"MailClient Value is not Valid."}}}
                return Response(content,status=status.HTTP_200_OK)

            csvFileId = data.get('csvFile')
            totalContacts = 0
            if not csvFileId:
                content = {"error2": { 1: { "message" :"csvFile Field is Required."}}}
                return Response(content,status=status.HTTP_200_OK)
            try:
                csvFile = FileUpload.objects.get(user=user,id=csvFileId)
            except:
                content = {"error2": { 1: { "message" :"CSV File Not Found."}}}
                return Response(content,status=status.HTTP_200_OK)
            try:
                allData = pd.read_csv(csvFile.media_file.path)
                allData = allData.fillna("")
                totalContacts = allData.shape[0]
                if totalContacts==0:
                    #content = {"csvFile": ["No Data Found Inside CSV."]}#{'errors': "No Data Found Inside CSV."}
                    content = {"error2": { 1: { "message" :"No Data Found Inside CSV."}}}
                    return Response(content,status=status.HTTP_200_OK)
                allColumns = allData.columns.tolist()
            except:
                content = {"error2": { 1: { "message" :"CSV file is not Valid."}}}
                return Response(content,status=status.HTTP_200_OK)
            reqMT = {}
            fData = {}

            
            mergeTagMap = data.get('mergeTagMap')
            for ii in mergeTag:
                try:
                    csvColumnName = mergeTagMap[ii]
                    if csvColumnName not in allColumns:
                        reqMT[ii]= [f'Map Column Name ({csvColumnName}) not found in CSV.']
                    else:
                        fData[ii] = csvColumnName
                except:
                    reqMT[ii]= ['This field is Required.']
                
            if len(reqMT)!=0:
                content = {"error2": { 1: { "message" :"Merge Tag Mapping is Not Valid.","data": reqMT}}}
                return Response(content,status=status.HTTP_200_OK)
                # content = {'errors': {'mergeTagMap': reqMT}}
                # return Response(content,status=status.HTTP_400_BAD_REQUEST)

            else:
                #validate csv
                finalData = []
                validEmail = []
                errors1 = {}
                errors0 = {}

                finalErrorCount = 0
                allCExcelIndex = {}
                for ii in fData:
                    allCExcelIndex[ii] = chr(65+allColumns.index(fData[ii]))


                for index, row in allData.iterrows():
                    uniqueIdentity = row[fData['{{GroupEmailId}}']]

                    currentData = {}
                    totalErrorCount = 0
                    #columnIndex = chr(65+allColumns.index())
                    errors1[index+1] = {"email": "","data": []}
                    if not uniqueIdentity.strip():
                        errors1[index+1]['data'].append({"message": "{Email Id} cannot be empty.","cellIndex": f"{allCExcelIndex['{{GroupEmailId}}']}{index+1}"})
                        totalErrorCount+=1
                    else:
                        try:
                            validate_email(uniqueIdentity)
                            errors1[index+1]['email'] = uniqueIdentity
                            if uniqueIdentity not in validEmail:
                                validEmail.append(uniqueIdentity)
                                currentData['uniqueIdentity'] = uniqueIdentity
                                
                            else:
                                errors1[index+1]['data'].append({"message": "{Email Id} should be unique.","cellIndex": f"{allCExcelIndex['{{GroupEmailId}}']}{index+1}"})
                                
                                totalErrorCount+=1
                        except:
                            errors1[index+1]['data'].append({"message": "{Email Id} should be a Valid Email.","cellIndex": f"{allCExcelIndex['{{GroupEmailId}}']}{index+1}"})
                            totalErrorCount+=1

                    try:
                        _ = CampaignProspect.objects.get(uniqueIdentity=uniqueIdentity,campaign=inst,solom__isnull=True)
                        errors0[index+1] = {"email": uniqueIdentity,"data": [{"message": "{Email Id} already exists in this campaign.","cellIndex": f"{allCExcelIndex['{{GroupEmailId}}']}{index+1}"}]}
                    except:
                        # not exist
                        pass

                    for ii in fData:
                        curntMData = row[fData[ii]]
                        if not curntMData.strip():
                            errors1[index+1]['data'].append({"message": f"{ii} cannot be empty.","cellIndex": f"{allCExcelIndex[ii]}{index+1}"})
                            totalErrorCount+=1
                        else:
                            if ii == "{WebsiteScreenshot}":
                                try:
                                    self.urlValidate(curntMData)
                                    currentData[ii] = curntMData
                                except:
                                    errors1[index+1]['data'].append({"message": f"{ii}  should be a Valid URL.","cellIndex": f"{allCExcelIndex[ii]}{index+1}"})
                                    totalErrorCount+=1
                            else:
                                currentData[ii] = curntMData
                                
                    if totalErrorCount==0:
                        finalData.append(currentData)
                    finalErrorCount+=totalErrorCount

                    if len(errors1[index+1]['data'])==0:
                        errors1.pop(index+1)

                
                #save csv
                df = pd.DataFrame(finalData)
                stinst = GroupCampaign(campaign=inst,mergeTagMap=json.dumps(fData),mailClient=mailClient,csvFile=csvFile,isValidated=True,isGenerated=False,totalData=len(allData))
                stinst.save()
                df.to_csv(stinst.getCsvPath(),index=False)
                isError = False
                if finalErrorCount>0 or len(errors0)>0:
                    isError = True
                content = {'id': str(stinst.id),'isError': isError,'totalSkipped': len(errors1),'totalErrors':  finalErrorCount,'errors0': errors0, 'errors1': errors1,'totalContacts': totalContacts,'previousUsed': len(errors0)}
                return Response(content,status=status.HTTP_200_OK)

        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


from datetime import datetime

def addToSingleGroup(inst,request):

    try:
        alreadyGenerated = []
        campaign = inst.campaign
        inst.isValidated = False
        inst.save()
        totalDurations = 0
        
        # for ii in campaign.video.generateStatus.generateScene.all():
        #     totalDurations+=ii.videoDuration

        alreadyGenerated = []
        
        totalgid = []
        totalAdded = 0
        csvData = pd.read_csv(inst.getCsvPath())
        
        for row in csvData.to_dict(orient='records'):
            uniqueIdentity = row['uniqueIdentity']
            if not uniqueIdentity.strip():
                continue

            tempDD = row.copy()
            tempDD.pop('uniqueIdentity')

            try:
                sgInst = GroupSingleCampaign(uniqueIdentity=uniqueIdentity,groupcampaign=inst,data=json.dumps(tempDD))
                sgInst.save()
            except Exception as e:
                print('Error in Single Group Camp: ',e)
                continue


            allSceneInst = campaign.video.singleScene.all()
            isVideoBg = False
            texts = []
            for tinst in allSceneInst:
                texts.append(tinst.getCustomParsedText(tempDD))
                if tinst.isSnapshotMergeTag and tinst.bgVideoType==5:
                    isVideoBg = True
            getUniqueData =campaign.video.getUniqueDataM(texts)


            if isVideoBg:
                getUniqueData = json.loads(getUniqueData)
                getUniqueData['{{WebsiteScreenshot}}'] = tempDD["{{WebsiteScreenshot}}"]
                getUniqueData = json.dumps(getUniqueData)

            finalGInstQ = GeneratedFinalVideo.objects.filter(multipleScene=campaign.video,output=getUniqueData,status=1)
            created = False
            if finalGInstQ.count()>=1:
                finalGInst = finalGInstQ.first()
                finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=campaign.video.name,isDefault=4,multipleScene=campaign.video,output=getUniqueData,video=finalGInst.video,status=1,groupCampaign=sgInst)
                if created:
                    finalGInst.onVideoComplete()
            else:
                finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=campaign.video.name,isDefault=4,multipleScene=campaign.video,output=getUniqueData,groupCampaign=sgInst)

            if created:
                finalGInst.thumbnailImage = campaign.selectedThumbnail.thumbnailImage
                finalGInst.save()

            finalGInst.setThumbnail(playButton=True)
            #finalGInst.setThumbnail()

            sgInst.genVideo = finalGInst

            finst = SalesPageEditorSerializer(campaign.salespage,context={'request': request}).data

            for ind,ii in enumerate(finst['textEditor']):
                text = ii['content']
                for ii in tempDD:
                    text = text.replace(ii,tempDD[ii])
                finst['textEditor'][ind]['content'] = text
            sgInst.salesPageData = json.dumps(finst)

            sgInst.save()
            
            totalAdded += 1


            totalgid.append(finalGInst.id)

        inst.isAdded = True
        inst.totalData = totalAdded
        inst.save()


        totalCreditUsed = ceil((campaign.video.generateStatus.totalFrames/60)/settings.VIDEOCREDIT_RATE)*totalAdded
        tminst = VideoCreditUsage(usedCredit=totalCreditUsed,user=campaign.user,usedCreditType=1,name=campaign.name,info=json.dumps({'gid': totalgid,'type': 'group','id': str(inst.id)}))
        tminst.save()

    except Exception as e:
        open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Group Single Campaign == {e} == {str(traceback.format_exc())}\n\n")



class GroupCampignGenerateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GroupCampaignSerializer

    def get_object(self, pk,user):
        try:
            return (True,GroupCampaign.objects.get(pk=pk,campaign__user=user))
        except GroupCampaign.DoesNotExist:
            return (False,'')

    def get(self,request,pk,format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if inst.isValidated:
                csvPath = inst.getCsvPath()
                th = Thread(target=addToSingleGroup,args=(inst,request))
                th.daemon = True
                th.start()

            serializers = self.serializer_class(inst,context={'request': request})
            content = {'result': serializers.data }
            return Response(content,status=status.HTTP_201_CREATED)

        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self,request,pk,format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if inst.isValidated:
                try:
                    os.remove(inst.getCsvPath())
                except:
                    pass
                inst.delete()
            return Response('',status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class EmailClientView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailClientSerializer

    def get(self, request, format=None):
        query = EmailClient.objects.all()
        sData = self.serializer_class(query,many=True,context={'request': request}).data
        content = {'results': sData}
        return Response(content,status=status.HTTP_200_OK)
