from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

from userlibrary.serializers import FileUploadSerializer
from userlibrary.models import FileUpload
from utils.imageProcessing import cropCenter

import magic
def file_path_mime(file_path):
    mime = magic.from_file(file_path, mime=True)
    return mime


def check_in_memory_mime(in_memory_file):
    mime = magic.from_buffer(in_memory_file.read(), mime=True)
    return mime


from django.core.files import File
import uuid,os,cv2
from pdf2image import convert_from_path
from django.core.files.base import ContentFile
#from wand.image import Image as wi

def add_pdf_thumbnail(instance):
    if not bool(instance.media_thumbnail):
        cache_dir = '_cache/'
        try:
            file_name = f"{instance.id}_{uuid.uuid4()}.jpeg"
            os.makedirs(cache_dir,exist_ok=True)
            image = convert_from_path(instance.media_file.path,single_file=True,fmt='jpeg',size=(720,None))[0]
            image = image.crop((0,0, 720, 405))
            image.save(cache_dir+file_name,quality=70)
            crntv = open(cache_dir+file_name,'rb')
            instance.media_thumbnail.save(file_name, File(crntv))
            crntv.close()
            os.remove(cache_dir+file_name)
        except Exception as e:
            print('Pdf thumbnail Error: ',e)

def add_video_thumbnail(instance):
    if not bool(instance.media_thumbnail):
        cache_dir = '_cache/'
        try:
            file_name = f"{instance.id}_{uuid.uuid4()}.jpeg"
            os.makedirs(cache_dir,exist_ok=True)
            os.system(f'ffmpeg -y -i "{instance.media_file.path}"  -vf "thumbnail" -vframes 1 {cache_dir+file_name}')
            
            crntv = open(cache_dir+file_name,'rb')
            instance.media_thumbnail.save(file_name, File(crntv))
            crntv.close()
            os.remove(cache_dir+file_name)
            
        except Exception as e:
            print("Thumbnail Errors: ",e)



class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50


from django.db.models import Q


def handleUploadFile(_instance,mime_type,process=0):
    filetype,ext = mime_type.split('/')
    if mime_type == 'image/gif':
        _instance.handleGif()
        add_video_thumbnail(_instance)
        return True
    elif filetype == 'video':
        _instance.handleVideo(process)
        add_video_thumbnail(_instance)
        
    elif mime_type == 'application/pdf':
        add_pdf_thumbnail(_instance)
    elif filetype == 'audio':
        _instance.setDuration()
    else:
        if filetype == 'image':
            _instance.imageThumbnail()
        else:
            _instance.media_thumbnail = None
    _instance.renameFile()
    return True


class FileUploadView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = FileUploadSerializer

    def get(self, request, format=None):

        user = request.user
        data = request.GET
        query = data.get('query','')
        type_ = data.get('type','')
        category = data.get('category','')
        orderBy = data.get('order','')

        type_q_objects = Q()
        if type_:
            for t in type_.split('_'):
                type_q_objects |= Q(media_type__icontains=t)




        if query and type_ and category:
            queryset = FileUpload.objects.filter(type_q_objects,user=user,name__icontains=query,category=category)
        elif query and type_:
            queryset = FileUpload.objects.filter(type_q_objects,user=user,name__icontains=query)
        elif category and type_:
            queryset = FileUpload.objects.filter(type_q_objects,user=user,category=category)
        elif query and category:
            queryset = FileUpload.objects.filter(user=user,name__icontains=query,category=category)
        elif category:
            queryset = FileUpload.objects.filter(user=user,category__in=category.split('_'))
        elif type_:
            queryset = FileUpload.objects.filter(type_q_objects,user=user)
        elif query:
            queryset = FileUpload.objects.filter(user=user,name__icontains=query)
        else:
            queryset = FileUpload.objects.filter(user=user)

        # 0 => A-Z
        # 1 => Z-A
        # 2 => Oldest - Newest
        # 3 => Newest - Oldest

        
        if orderBy in ['0','1','2','3']:
            if orderBy == '0':
                queryset = queryset.order_by('name')
            elif orderBy == '1':
                queryset = queryset.order_by('-name')
            elif orderBy == '2':
                queryset = queryset.order_by('timestamp')
            else:
                queryset = queryset.order_by('-timestamp')
        else:
            queryset = queryset.order_by('-timestamp')
            

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)

    def post(self, request, format=None):
        user = request.user
        media_file = request.data.get('media_file',None)
        _isPublic = request.data.get("isPublic",None)
        _isProcess = request.GET.get("process",0)
        _name = request.data.get("name",None)
        if media_file:
            mime_type = check_in_memory_mime(media_file)
            serializer = self.serializer_class(data=request.data,context={'request': request})
            if serializer.is_valid():
                serializer.validated_data['name'] = '.'.join(serializer.validated_data['name'].split('.')[:-1])
                inst = serializer.save(user=user,media_type=mime_type)
                handleUploadFile(serializer.instance,mime_type,process=_isProcess)
                isUpdate = False
                if _isPublic:
                    inst.isPublic = True
                    isUpdate = True
                if _name:
                    inst.name = _name
                    isUpdate = True
                if isUpdate:
                    inst.save()
                
                if inst.category == 'thumbnail':
                    try:
                        tempImg = cropCenter(inst.media_file.path)
                        ret, buf = cv2.imencode('.jpg', tempImg)
                        content = ContentFile(buf.tobytes())
                        os.remove(inst.media_file.path)
                        inst.media_file.save(f'{uuid.uuid4()}.jpg', content)
                    except:
                        pass
                return Response(serializer.data)
        
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"media_file": "This Field is Required."},status=status.HTTP_400_BAD_REQUEST)


class FileUploadDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = FileUploadSerializer

    def get_object(self, pk,user):
        try:
            return (True,FileUpload.objects.get(pk=pk,user=user))
        except FileUpload.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            serializer = self.serializer_class(inst,context={'request': request})
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
        

    def put(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        reqData = request.data
        _isPublic = reqData.get("isPublic",None)
        if is_exist:
            serializer = self.serializer_class(inst, data=request.data,partial=True,context={'request': request})
            if serializer.is_valid():
                if 'media_file' in reqData:
                    mime_type = check_in_memory_mime(reqData['media_file'])
                    inst = serializer.save(media_type=mime_type)
                    handleUploadFile(serializer.instance,mime_type)
                    # filetype,ext = mime_type.split('/')
                    # if filetype == 'video':
                    #     add_video_thumbnail(serializer.instance)
                    #     serializer.instance.setDuration()
                    # elif mime_type == 'application/pdf':
                    #     add_pdf_thumbnail(serializer.instance)
                    # elif filetype == 'audio':
                    #     serializer.instance.setDuration()
                    # else:
                    #     serializer.instance.media_thumbnail = None

                    if inst.category == 'thumbnail':
                        try:
                            tempImg = cropCenter(inst.media_file.path)
                            ret, buf = cv2.imencode('.jpg', tempImg)
                            content = ContentFile(buf.tobytes())
                            os.remove(inst.media_file.path)
                            inst.media_file.save(f'{uuid.uuid4()}.jpg', content)
                        except:
                            pass
                serializer.save()
                if _isPublic:
                    inst.isPublic = True
                    inst.save()
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


from django.contrib.auth import get_user_model
from campaign.models import (
    MainCampaign,GroupCampaign,
    GroupSingleCampaign,SoloCampaign
    )
from campaignAnalytics.models import (
    CampaignProspect,CampaignSingleAnalytics,
    CampaignGroupAnalytics
)
from aiQueueManager.models import GeneratedFinalVideo
import json
from datetime import datetime,timedelta
from django.utils import timezone
import random

from salesPage.serializers import (
    SalesPageEditorSerializer
)


class ResetDashBoardView(APIView,LimitOffset):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        cred = request.GET.get('secret',None)
        if cred =='OnlyLimitedPersonAllowed':
            userEmail = "overview@autogenerate.ai"
            userInst = get_user_model().objects.get(email=userEmail)

            campaignId = "9c07bdad-2a96-4a2e-900a-a0c0d11166b9"
            mainCampaign = MainCampaign.objects.get(id=campaignId)
            request.user = userInst
            salesPageJsonD = json.dumps(SalesPageEditorSerializer(mainCampaign.salespage,context={'request': request}).data)

            #salesPageJsonD = "{\"id\":395,\"name\":\"Salesforce <> Autogenerate.ai\",\"textEditor\":[{\"id\":1577,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"font-family: Poppins; font-size: 2.5vw; font-weight: 900; font-stretch: normal; font-style: normal; line-height: 1.46; letter-spacing: 1.44px; text-align: center; color: rgb(231, 65, 106);\\\"><span style=\\\"font-size: 1.66667vw;\\\">Salesforce &lt;&gt; AutoGenerate.ai</span></p>\",\"isDeleted\":false},{\"id\":1578,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"font-family: Poppins; font-size: 1.25vw; font-weight: 900; font-stretch: normal; font-style: normal; line-height: 1.46; letter-spacing: 0.48px; text-align: center; color: rgb(255, 252, 242);\\\">Scalable Human Connections for David</p>\",\"isDeleted\":false},{\"id\":1579,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"color: rgb(231, 65, 106);\\\"><strong style=\\\"font-size: 2.1875vw; color: rgb(231, 65, 106);\\\">Enter Your Text</strong></p>\",\"isDeleted\":true},{\"id\":1580,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"color: rgb(34, 34, 34);\\\"><strong style=\\\"font-size: 1.25vw; color: rgb(34, 34, 34);\\\">johndoe@gmail.com | +1 187187 XXXX</strong></p>\",\"isDeleted\":true}],\"imageEditor\":[{\"id\":395,\"image\":\"https://api.autogenerate.ai/media/userlibrary/file/autogenerate.ai_logo_EgraJCH.svg\",\"height\":55,\"imgUrl\":\"https://autogenerate.ai\",\"isDeleted\":false}],\"buttonEditor\":[{\"id\":395,\"buttonData\":[{\"id\":2270,\"name\":\"Schedule Demo\",\"link\":\"http://autogenerate.ai/\",\"textColor\":\"#ffffffff\",\"buttonColor\":\"#e7416a\",\"isDeleted\":false,\"updated\":\"2021-07-12T15:42:21.432423Z\"},{\"id\":2271,\"name\":\"Button2\",\"link\":\"http://fb.com/\",\"textColor\":\"#FF0000\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-12T15:42:21.435200Z\"},{\"id\":2272,\"name\":\"Button3\",\"link\":\"http://fb.com/\",\"textColor\":\"#FF0000\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-12T15:42:21.437911Z\"},{\"id\":2273,\"name\":\"Button4\",\"link\":\"http://fb.com/\",\"textColor\":\"#FF0000\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-12T15:42:21.440461Z\"},{\"id\":2274,\"name\":\"button\",\"link\":\"\",\"textColor\":\"#e6e6e6\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-12T15:42:21.442837Z\"},{\"id\":2275,\"name\":\"button\",\"link\":\"\",\"textColor\":\"#e6e6e6\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-12T15:42:21.445433Z\"},{\"id\":2276,\"name\":\"button\",\"link\":\"\",\"textColor\":\"#e6e6e6\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-12T15:42:21.447835Z\"}],\"isDeleted\":false}],\"iconEditor\":[{\"id\":1183,\"image\":\"https://api.autogenerate.ai/media/static/fbtemplate.svg\",\"link\":\"https://fb.com/\",\"isDeleted\":false},{\"id\":1184,\"image\":\"https://api.autogenerate.ai/media/static/linkedtemplate.svg\",\"link\":\"https://twitter.com/\",\"isDeleted\":false},{\"id\":1185,\"image\":\"https://api.autogenerate.ai/media/static/squaretemplate.svg\",\"link\":\"https://linkedin.com/\",\"isDeleted\":false}],\"videoEditor\":[{\"id\":395,\"height\":0,\"isDeleted\":false}],\"crouselEditor\":[{\"id\":395,\"crouselData\":[{\"id\":666,\"name\":\"Demo Video\",\"media_type\":\"video/mp4\",\"media_file\":\"https://api.autogenerate.ai/media/userlibrary/file/27c7e5cc-c2ef-11eb-bf88-fd9d708cc435_FfKQaRc_s0pt4Rb.mp4\",\"media_thumbnail\":\"https://api.autogenerate.ai/media/userlibrary/thumbnail/output_dGyUEj2.jpg\",\"category\":\"upload\",\"timestamp\":\"2021-07-11T11:42:49.079934Z\",\"updated\":\"2021-07-12T15:57:29.434301Z\",\"bgType\":4},{\"id\":664,\"name\":\"Infographics\",\"media_type\":\"application/pdf\",\"media_file\":\"https://api.autogenerate.ai/media/userlibrary/file/collateral_infographic.pdf\",\"media_thumbnail\":\"https://api.autogenerate.ai/media/userlibrary/thumbnail/664_4f1fd8d5-d988-4dc5-8d37-034514f79e61.jpeg\",\"category\":\"upload\",\"timestamp\":\"2021-07-11T11:41:21.296946Z\",\"updated\":\"2021-07-11T11:45:19.290812Z\"}],\"isDeleted\":false}],\"themeColorConfig\":{\"disabled\":false,\"colors\":{\"0\":\"#e7416a\",\"1\":\"#fffcf2\",\"2\":\"#222222\"}},\"publicId\":3,\"isPublish\":true,\"publicThemeColorCofig\":{\"disabled\":false,\"colors\":{\"0\":\"#e7416a\",\"1\":\"#fffcf2\",\"2\":\"#222222\"}}}"
            
            COMMAND = (
                (0,'SENT'),
                (2,'OPENED'),
                (3,'VIDEO PLAYED'),
                (4,'CTA CLICKED'),
                (5,'CROUSEL CLICKED')
            )
            GCOMMAND = (
                (0,'SENT'),
                (1,'MAIL OPENED'),
                (2,'OPENED'),
                (3,'VIDEO PLAYED'),
                (4,'CTA CLICKED'),
                (5,'CROUSEL CLICKED')
            )


            #relative time in Seconds as int and str as static time
            signalsData = [
                {"uniqueIdentity": "david@salesforce.com","type": "group","command": 4,"campaign": "Book Meetings","data": {"name": "Schedule Demo"}, "time": 0},
                {"uniqueIdentity": "david@salesforce.com","type": "group","command": 5,"campaign": "Book Meetings","data": {"name": "Demo Video"}, "time": 2*60},
                {"uniqueIdentity": "Oliver-Zoho on LinkedIn","type": "solo","command": 2,"campaign": "Book Meetings","data": {}, "time": 5*60},
                {"uniqueIdentity": "Oliver-Zoho on LinkedIn","type": "solo","command": 0,"campaign": "Book Meetings","data": {}, "time": 15*60},
                {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 3,"campaign": "New Subscription","data": {"name": "Explainer Video"}, "time": 7*60},
                {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 2,"campaign": "New Subscription","data": {}, "time": 9*60},
                {"uniqueIdentity": "david@salesforce.com","type": "group","command": 3,"campaign": "Book Meetings", "data": {"name": "Sales Pitch"},"time": 8 * 60},
                {"uniqueIdentity": "david@salesforce.com","type": "group","command": 2,"campaign": "Book Meetings", "data": {},"time": 9 * 60},
                {"uniqueIdentity": "david@salesforce.com","type": "group","command": 1,"campaign": "Book Meetings", "data": {},"time": 10 * 60},
                {"uniqueIdentity": "david@salesforce.com","type": "group","command": 0,"campaign": "Book Meetings", "data": {},"time": 15 * 60},
                {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 5,"campaign": "Trial Activation","data": {"name": "Infographics"}, "time": 12*60},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 4,"campaign": "Book Meetings","data": {"name": "Schedule Demo"}, "time": 17*60},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 5,"campaign": "Book Meetings","data": {"name": "Infographics"}, "time": 18*60},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 3,"campaign": "Book Meetings","data": {"name": "Sales Pitch"}, "time": 20*60},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 2,"campaign": "Book Meetings","data": {}, "time": 21*60},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 1,"campaign": "Book Meetings","data": {}, "time": 22*60},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 0,"campaign": "Book Meetings","data": {}, "time": 25*60},

                #prospect data
                {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 3,"campaign": "Trial Activation","data": {"name": "Explaner Video"}, "time": 12*60*60 + 58*60},
                {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 2,"campaign": "Trial Activation","data": {}, "time": 12*60*60 + 59*60},
                {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 1,"campaign": "Trial Activation","data": {}, "time": 13*60*60 + 3*60},
                {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 0,"campaign": "Trial Activation","data": {}, "time": 15*60*60 + 3*60},
                {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 1,"campaign": "New Subscription","data": {}, "time": "29-06-2021T19:39"},
                {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 0,"campaign": "New Subscription","data": {}, "time": "28-06-2021T19:38"},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 3,"campaign": "AutoGenerate Product...","data": {"name": "Sales Pitch"}, "time": "16-06-2021T17:09"},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 2,"campaign": "AutoGenerate Product...","data": {}, "time": "16-06-2021T17:08"},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 1,"campaign": "AutoGenerate Product...","data": {}, "time": "16-06-2021T17:04"},
                {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 0,"campaign": "AutoGenerate Product...","data": {}, "time": "16-06-2021T13:04"},

            ]


            salespageD = json.loads(salesPageJsonD)
            mainCtaData = {}
            for i in salespageD['buttonEditor']:
                if i['isDeleted'] == False:
                    for j in i['buttonData']:
                        if j['isDeleted'] == False:
                            mainCtaData[j['id']] = {'name': j['name'],'isClicked': False}

            mainCollateralData = {}
            for i in salespageD['crouselEditor']:
                if i['isDeleted'] == False:
                    for j in i['crouselData']:
                        mainCollateralData[j['id']] = {'name': j['name'],'isClicked': False}



            PSTATUS = (
                (0,'Pending'),
                (1,'Meeting Booked'),
                (2,'Snooze for 7 Days'),
                (3,'Snooze for 30 Days'),
                (4,'Sale Success'),
                (5,'Nothing Saled'),

            )



            prospectStatus = {"david@salesforce.com": 1,"sophia@chorus.ai": 4}

            prospectOrder = []
            prospectType = []
            for ii in signalsData:
                uid = ii['uniqueIdentity']+'__'+ii['campaign']
                if uid not in prospectOrder:
                    prospectOrder.append(uid)
                    prospectType.append(ii['type'])
            prospectType = prospectType[::-1]
            prospectOrder = prospectOrder[::-1]
            print(prospectOrder)




            campaignCtaBtn = {}
            campaignColBtn = {}
            videoData = {}
            for ii in signalsData:
                try:
                    campaignCtaBtn[ii['campaign']]
                except:
                    campaignCtaBtn[ii['campaign']] = []
                try:
                    campaignColBtn[ii['campaign']]
                except:
                    campaignColBtn[ii['campaign']] = []
                if ii['command'] == 3:
                    videoData[ii['uniqueIdentity']+'__'+ii['campaign']]=  json.dumps({'name': ii['data']['name'],'isClicked': False})
                if ii['command'] == 4:
                    campaignCtaBtn[ii['campaign']].append(ii['data']['name'])
                elif ii['command'] == 5:
                    campaignColBtn[ii['campaign']].append(ii['data']['name'])

            finalCtaPCamp = {}
            campaignCtaData = {}
            for ii in campaignCtaBtn:
                tdata = list(set(campaignCtaBtn[ii]))
                if len(tdata)==0:
                    tdata = ['Book Meetings','Visit Website']
                mainD = {}
                if ii == mainCampaign.name:
                    for jj in mainCtaData:
                        data = mainCtaData[jj]
                        try:
                            campaignCtaData[ii][data['name']]= jj
                        except:
                            campaignCtaData[ii]={data['name']: jj}
                    mainD = mainCtaData
                else:
                    for n,jj in enumerate(tdata):
                        mainD[n]= {'name': jj,'isClicked': False}
                        try:
                            campaignCtaData[ii][jj]=n
                        except:
                            campaignCtaData[ii]={jj: n}
                finalCtaPCamp[ii] = json.dumps(mainD)

            finalColPCamp = {}
            campaignColData = {}
            for ii in campaignColBtn:
                tdata = list(set(campaignColBtn[ii]))
                if len(tdata)==0:
                    tdata = ['Demo Video','Infographics']
                mainD = {}
                if ii == mainCampaign.name:
                    for jj in mainCollateralData:
                        data = mainCollateralData[jj]
                        try:
                            campaignColData[ii][data['name']]= jj
                        except:
                            campaignColData[ii]={data['name']: jj}
                    mainD = mainCollateralData
                else:
                    for n,jj in enumerate(tdata):
                        mainD[n]= {'name': jj,'isClicked': False}
                        try:
                            campaignColData[ii][jj]=n
                        except:
                            campaignColData[ii]={jj: n}
                finalColPCamp[ii] = json.dumps(mainD)




            createNewCampaign = []
            allGroup = {}
            allSolo = {}
            for anaylData in signalsData:
                if anaylData['campaign'] not in createNewCampaign:
                    createNewCampaign.append(anaylData['campaign'])
                    if anaylData['type'] == 'group':
                        allGroup[anaylData['campaign']] = [anaylData['uniqueIdentity']]
                        allSolo[anaylData['campaign']] = []
                    else:
                        allSolo[anaylData['campaign']] = [anaylData['uniqueIdentity']]
                        allGroup[anaylData['campaign']] =[]
                else:
                    if anaylData['type'] == 'group':
                        if anaylData['uniqueIdentity'] not in allGroup[anaylData['campaign']]:
                            allGroup[anaylData['campaign']].append(anaylData['uniqueIdentity'])
                    else:
                        if anaylData['uniqueIdentity'] not in allSolo[anaylData['campaign']]:
                            allSolo[anaylData['campaign']].append(anaylData['uniqueIdentity'])

                    

            campaignInst = {}
            for nn,campName in enumerate(createNewCampaign):
                try:
                    inst = MainCampaign.objects.get(user=userInst,name=campName)
                    campaignInst[campName] = inst
                except:
                    inst = MainCampaign(user=userInst,name=campName,video=mainCampaign.video,salespage=mainCampaign.salespage)
                    inst.save()
                    campaignInst[campName] = inst
                if nn == 0:
                    _newDateTimestamp = datetime.today() - timedelta(days=1)
                else:
                    _newDateTimestamp = datetime.today() - timedelta(days=random.randint(nn*2,(nn+1)*2))
                inst.timestamp = _newDateTimestamp
                inst.updated = _newDateTimestamp
                inst.save()



            groupDataInst = {}
            ## create group campaign
            jobTitle = {"david@salesforce.com": "Sales Team Lead","emma@dropbox.com": "Sales Manager"}
            _jobTitle = ["Senior Marketing Manager","Demand Generation Manager","Head of Sales","Account Manager","Associate Director","Senior Account Manager"]
            _csFile = [FileUpload.objects.get(id=1),FileUpload.objects.get(id=3)]
            _time = [2*60*60,5*60*60,7*60*60,10*60*60,20*60*60,23*60*60]
            for indx,singleCamp in enumerate(allGroup):
                campData = allGroup[singleCamp]
                inst = GroupCampaign.objects.filter(campaign=campaignInst[singleCamp])
                if inst:
                    inst.delete()
                inst = GroupCampaign(campaign=campaignInst[singleCamp],mergeTagMap=json.dumps({"{{GroupEmailId}}": "email","{{Name}}": "Name","{{Company}}": "Company","{{Job Title}}": "Job Title","{{WebsiteScreenShot}}": "Website"}),isAdded=True,isValidated=False,totalData=len(campData),isGenerated=True)
                inst.csvFile=_csFile[indx%len(_csFile)]
                inst.save()
                inst.timestamp = timezone.now() - timedelta(0,_time[indx%len(_time)])
                inst.save()

                if campaignInst[singleCamp].name == "Book Meetings":
                    _campData = {
                        "rogerspl@sbcglobal.net": {"name": "Bob Frapples","company": "Sbcglobal","website": "https://www.sbcglobal.net/","job": "Vice President"},
                        "dburrows@yahoo.com": {"name": "Walter Melon","company": "Yahoo","website": "https://www.yahoo.com/","job": "Sales Manager"},
                        "anna@comcast.net": {"name": "Anna Sthesia","company": "Comcast","website": "https://www.comcast.net/","job": "Head of Sales"},
                        "paul@atlassian.com": {"name": "Paul Molive","company": "Atlassian","website": "https://www.atlassian.com/","job": "Account Manager"},
                        "anna.mull@hubspot.com": {"name": "Anna Mull","company": "Hubspot","website": "https://www.hubspot.com/","job": "Associate Director"},
                        "gail@adobe.com": {"name": "Gail Forcewind","company": "Adobe","website": "https://www.adobe.com/","job": "Senior Account Manager"},
                        "paige@mailchimp.com": {"name": "Paige Turner","company": "MailChimp","website": "https://www.mailchimp.com/","job": "Sales Executive"},
                        "peter@salesforce.com": {"name": "Peter Cruiser","company": "Salesforce","website": "https://www.salesforce.com/in/","job": "Senior Marketing Manager"},
                        "mario@slack.com": {"name": "Mario Speedwagon","company": "Slack","website": "https://www.slack.com/","job": "Demand Generation Manager"},
                        "emma@dropbox.com": {"name": "Emma","company": "Dropbox","website": "https://www.dropbox.com/","job": "Sales Manager"},
                        "david@salesforce.com": {"name": "David","company": "Salesforce","website": "https://www.salesforce.com/in/","job": "Sales Team Lead"},

                    }
                    inst.totalData = len(_campData)
                    inst.save()
                    for nn,unQi in enumerate(_campData):
                        _varData = {"{{GroupEmailId}}": unQi,"{{Name}}": _campData[unQi]['name'],"{{Company}}": _campData[unQi]['company'],"{{Job Title}}": _campData[unQi]['job'],"{{WebsiteScreenShot}}": _campData[unQi]['website']}
                        _salesPageJsonD = json.loads(salesPageJsonD)
                        for ind,ii in enumerate(_salesPageJsonD['textEditor']):
                            text = ii['content']
                            for ii in _varData:
                                text = text.replace(ii,_varData[ii])
                            _salesPageJsonD['textEditor'][ind]['content'] = text

                        try:
                            sgroupInst = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=unQi)
                            sgroupInst.salesPageData=json.dumps(_salesPageJsonD)
                        except:
                            sgroupInst = GroupSingleCampaign(groupcampaign=inst,uniqueIdentity=unQi,genVideo=campaignInst[singleCamp].video.generateStatus,salesPageData=json.dumps(_salesPageJsonD))
                        
                        if unQi == "david@salesforce.com":
                            try:
                                _genVideo = GeneratedFinalVideo.objects.get(id=1260)
                                sgroupInst.genVideo = _genVideo
                            except:
                                pass
                        else:
                            try:
                                _genVideo = GeneratedFinalVideo.objects.get(id=1262)
                                sgroupInst.genVideo = _genVideo
                            except:
                                pass

                        sgroupInst.data=json.dumps(_varData)
                        sgroupInst.save()
                        groupDataInst[unQi+'__'+singleCamp] = sgroupInst



                
                    indx += 1
                    inst = GroupCampaign(campaign=campaignInst[singleCamp],mergeTagMap=json.dumps({"{{GroupEmailId}}": "email","{{Name}}": "Name","{{Company}}": "Company","{{Job Title}}": "Job Title","{{WebsiteScreenShot}}": "Website"}),isAdded=True,isValidated=False,totalData=len(campData),isGenerated=True)
                    inst.csvFile=_csFile[indx%len(_csFile)]
                    inst.save()
                    inst.timestamp = timezone.now() - timedelta(0,_time[indx%len(_time)])
                    inst.save()
                    for nn,unQi in enumerate(campData):
                        if unQi == "david@salesforce.com":
                            unQi = "ali@salesforce.com"
                        elif unQi == "emma@dropbox.com":
                            unQi = "malika@salesforce.com"
                        _job = None
                        try:
                            _job = jobTitle[unQi]
                        except:
                            _job = _jobTitle[nn%len(_jobTitle)]
                        _varData = {"{{GroupEmailId}}": unQi,"{{Name}}": unQi.split('@')[0].capitalize(),"{{Company}}": "Salesforce","{{Job Title}}": _job,"{{WebsiteScreenShot}}": "https://www.salesforce.com/in/"}
                        _salesPageJsonD = json.loads(salesPageJsonD)
                        for ind,ii in enumerate(_salesPageJsonD['textEditor']):
                            text = ii['content']
                            for ii in _varData:
                                text = text.replace(ii,_varData[ii])
                            _salesPageJsonD['textEditor'][ind]['content'] = text

                        try:
                            sgroupInst = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=unQi)
                            sgroupInst.salesPageData=json.dumps(_salesPageJsonD)
                        except:
                            sgroupInst = GroupSingleCampaign(groupcampaign=inst,uniqueIdentity=unQi,genVideo=campaignInst[singleCamp].video.generateStatus,salesPageData=json.dumps(_salesPageJsonD))
                        
                        if unQi == "david@salesforce.com":
                            try:
                                _genVideo = GeneratedFinalVideo.objects.get(id=1260)
                                sgroupInst.genVideo = _genVideo
                            except:
                                pass
                        elif unQi == "emma@dropbox.com":
                            try:
                                _genVideo = GeneratedFinalVideo.objects.get(id=1262)
                                sgroupInst.genVideo = _genVideo
                            except:
                                pass
                        sgroupInst.data=json.dumps(_varData)
                        sgroupInst.save()
                        #groupDataInst[unQi+'__'+singleCamp] = sgroupInst

                else:
                    for nn,unQi in enumerate(campData):
                        _varData = {"{{GroupEmailId}}": unQi,"{{Name}}": unQi.split('@')[0].capitalize(),"{{Company}}": "Salesforce","{{Job Title}}": "Manager","{{WebsiteScreenShot}}": "https://www.salesforce.com/in/"}
                        _salesPageJsonD = json.loads(salesPageJsonD)
                        for ind,ii in enumerate(_salesPageJsonD['textEditor']):
                            text = ii['content']
                            for ii in _varData:
                                text = text.replace(ii,_varData[ii])
                            _salesPageJsonD['textEditor'][ind]['content'] = text

                        try:
                            sgroupInst = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=unQi)
                            sgroupInst.salesPageData=json.dumps(_salesPageJsonD)
                        except:
                            sgroupInst = GroupSingleCampaign(groupcampaign=inst,uniqueIdentity=unQi,genVideo=campaignInst[singleCamp].video.generateStatus,salesPageData=json.dumps(_salesPageJsonD))
                        
                        if unQi == "david@salesforce.com":
                            try:
                                _genVideo = GeneratedFinalVideo.objects.get(id=1260)
                                sgroupInst.genVideo = _genVideo
                            except:
                                pass
                        else:
                            try:
                                _genVideo = GeneratedFinalVideo.objects.get(id=1262)
                                sgroupInst.genVideo = _genVideo
                            except:
                                pass

                        sgroupInst.data=json.dumps(_varData)
                        sgroupInst.save()
                        groupDataInst[unQi+'__'+singleCamp] = sgroupInst
            soloDataInst = {}
            for singleCamp in allSolo:
                campData = allSolo[singleCamp]
                for nn,unQi in enumerate(campData):
                    _job = _jobTitle[nn%len(_jobTitle)]
                    _name = unQi.split(' ')[0].capitalize()
                    if unQi == "Oliver-Zoho on LinkedIn":
                        _name = "Oliver"
                        _job = "Sales Executive"
                        
                    _varData = {"{{GroupEmailId}}": unQi,"{{Name}}": _name,"{{Company}}": "Salesforce","{{Job Title}}": _job,"{{WebsiteScreenShot}}": "https://www.salesforce.com/in/"}
                    _salesPageJsonD = json.loads(salesPageJsonD)
                    for ind,ii in enumerate(_salesPageJsonD['textEditor']):
                        text = ii['content']
                        for ii in _varData:
                            text = text.replace(ii,_varData[ii])
                        _salesPageJsonD['textEditor'][ind]['content'] = text

                    try:
                        sgroupInst = SoloCampaign.objects.get(uniqueIdentity=unQi,campaign=campaignInst[singleCamp])
                        sgroupInst.salesPageData=json.dumps(_salesPageJsonD)
                    except:
                        sgroupInst = SoloCampaign(uniqueIdentity=unQi,campaign=campaignInst[singleCamp],genVideo=campaignInst[singleCamp].video.generateStatus,salesPageData=json.dumps(_salesPageJsonD))
                    if unQi == "Oliver-Zoho on LinkedIn":
                        try:
                            _genVideo = GeneratedFinalVideo.objects.get(id=1261)
                            sgroupInst.genVideo = _genVideo
                        except:
                            pass
                    sgroupInst.data=json.dumps(_varData)
                    sgroupInst.save()
                    soloDataInst[unQi+'__'+singleCamp] = sgroupInst

            ## create Prospect
            mainProspect = {}
            for nn,uniqueIdentity in enumerate(prospectOrder):
                if prospectType[nn] == 'group':
                    groupInstC = groupDataInst[uniqueIdentity]
                    uniqueIdentity = uniqueIdentity.split('__')[0]
                    crntInst = CampaignProspect.objects.filter(campaign=groupInstC.groupcampaign.campaign,uniqueIdentity=uniqueIdentity,groupm=groupInstC)
                    for ii in crntInst:
                        ii.delete()

                    crntInst = CampaignProspect(campaign=groupInstC.groupcampaign.campaign,uniqueIdentity=uniqueIdentity,groupm=groupInstC)
                    crntInst.save()
                    
                    crntInst.ctaData = finalCtaPCamp[groupInstC.groupcampaign.campaign.name]
                    try:
                        crntInst.videoData = videoData[uniqueIdentity]
                    except:
                        pass
                    crntInst.collateralData = finalColPCamp[groupInstC.groupcampaign.campaign.name]
                    crntInst.save()
                    mainProspect[uniqueIdentity+'__'+crntInst.campaign.name]=crntInst
                else:
                    groupInstC = soloDataInst[uniqueIdentity]
                    uniqueIdentity = uniqueIdentity.split('__')[0]

                    crntInst = CampaignProspect.objects.filter(campaign=groupInstC.campaign,uniqueIdentity=uniqueIdentity,solom=groupInstC)
                    for ii in crntInst:
                        ii.delete()

                    crntInst = CampaignProspect(campaign=groupInstC.campaign,uniqueIdentity=uniqueIdentity,solom=groupInstC)
                    crntInst.save()
                    crntInst.ctaData = finalCtaPCamp[groupInstC.campaign.name]
                    crntInst.collateralData = finalColPCamp[groupInstC.campaign.name]
                    try:
                        crntInst.videoData = videoData[uniqueIdentity]
                    except:
                        pass
                    crntInst.save()
                    mainProspect[uniqueIdentity+'__'+crntInst.campaign.name]=crntInst

          
            

            updatedTime = {}
            ## add data to signals
            for ii in signalsData:
                if ii['type'] != 'group':
                    _query = CampaignSingleAnalytics.objects.filter(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']])
                    if _query:
                        _query.delete()
                else:
                    _query = CampaignGroupAnalytics.objects.filter(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']])
                    if _query:
                        _query.delete()

            for ii in signalsData:
                #relative time
                if type(ii['time'])==int:
                    now = timezone.now()
                    timeDateTime = now - timedelta(0,ii['time'])
                else:
                    timeDateTime = datetime.strptime(ii['time'], '%d-%m-%YT%H:%M').replace(tzinfo=timezone.utc)

                if ii['type'] != 'group':
                    if ii['command'] == 0:
                        try:
                            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
                        except:
                            allQ = CampaignSingleAnalytics.objects.filter(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
                            allQ.delete()
                            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
                    elif ii['command'] == 2:
                        try:
                            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
                        except:
                            allQ = CampaignSingleAnalytics.objects.filter(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
                            allQ.delete()
                            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
                    elif ii['command'] == 3:
                        inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=3,data=str(0),cData=json.dumps({'name': ii['data']['name']}))
                    elif ii['command'] == 4:
                        btnName = ii['data']['name']
                        vdata = campaignCtaData[ii['campaign']][btnName]
                        cData = {'id': vdata,'name': btnName}
                        inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=4,data=str(vdata),cData=json.dumps(cData))
                    elif ii['command'] == 5:
                        btnName = ii['data']['name']
                        vdata = campaignColData[ii['campaign']][btnName]
                        cData = {'id': vdata,'name': btnName}
                        inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=5,data=str(vdata),cData=json.dumps(cData))
                    inst_.timestamp=timeDateTime
                    inst_.save()

                else:
                    
                    if ii['command'] == 0:
                        inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
                    elif ii['command'] == 1:
                        inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=1)
                    elif ii['command'] == 2:
                        inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
                    elif ii['command'] == 3:
                        inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=3,data=str(0),cData=json.dumps({'name': ii['data']['name']}))
                    elif ii['command'] == 4:
                        btnName = ii['data']['name']
                        vdata = campaignCtaData[ii['campaign']][btnName]
                        cData = {'id': vdata,'name': btnName}
                        inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=4,data=str(vdata),cData=json.dumps(cData))
                    elif ii['command'] == 5:
                        btnName = ii['data']['name']
                        vdata = campaignColData[ii['campaign']][btnName]
                        cData = {'id': vdata,'name': btnName}
                        inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=5,data=str(vdata),cData=json.dumps(cData))
                    inst_.timestamp=timeDateTime
                    inst_.save()

                try:
                    getPrvTime = updatedTime[ii['uniqueIdentity']+'__'+ii['campaign']]
                    if getPrvTime<timeDateTime:
                        updatedTime[ii['uniqueIdentity']+'__'+ii['campaign']] = timeDateTime
                except:
                    updatedTime[ii['uniqueIdentity']+'__'+ii['campaign']] = timeDateTime


            for ii in updatedTime:
                tmp = mainProspect[ii]
                print(tmp.id,updatedTime[ii])
                t = CampaignProspect.objects.filter(id=tmp.id)
                t.update(updated=updatedTime[ii])


            for ii in prospectStatus:
                tmp = CampaignProspect.objects.filter(uniqueIdentity=ii)
                tmp.update(prospectStatus=prospectStatus[ii])

            content = {'message': 'Completed'}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'message': 'Not Allowd'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)