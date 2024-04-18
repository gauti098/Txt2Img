from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer

import asyncio
import json,time
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer

from django.conf import settings
from aiQueueManager.models import GeneratedFinalVideo,SnapshotUrl
from aiQueueManager.serializers import GenerateFinalVideoSerializer
from campaign.models import GroupSingleCampaign
from videoThumbnail.models import MainThumbnail

from subscriptions.models import VideoCreditUsage
from math import ceil
from campaign.views import sendGroupCampaignEmail
from threading import Thread
from aiQueueManager.generateAudio import generateAudio


class SetThumbnailConsumer(WebsocketConsumer):

    def connect(self):
        headers = self.scope['query_string'].split(b'token=')
        if len(headers)>1 and settings.WEBSOCKET_SERVER_TOKEN == headers[1].decode():
            self.group_name = 'generateThumbnail'
            async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
            self.accept()
        else:
            self.close()
            
    def receive(self,text_data):
        mainData = json.loads(text_data)
        if mainData["type"] == "sendToUser":
            _user = mainData.get("user",None)
            if _user:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    str(_user),
                    {
                        "type": "sendSignals",
                        "text": {"type": mainData["returnType"],"data": mainData["returnData"]},
                    },
                )
        elif mainData["type"] == "generateAudio":
            generateAudio(mainData["data"])
        elif mainData["type"] == "videoCompleted":
            inst = GeneratedFinalVideo.objects.get(id=mainData["id"])
            inst.isVideoGenerated = True
            inst.save()
            if inst.combineAudioVideo():
                inst.onVideoComplete()

            # if inst.isDefault==1:
            #     signalData = {"type": "mainVideoProgressUpdate","data":  {"id": inst.multipleScene.id,"status": 1,"completedPercentage": 100,"isDefault": inst.isDefault} }
            # elif inst.isDefault == 2:
            #     videoDetailsD = GenerateFinalVideoSerializer(inst).data
            #     videoDetailsD['video'] = settings.BASE_URL + videoDetailsD['video']
            #     videoDetailsD['thumbnailImage'] = settings.BASE_URL + videoDetailsD['thumbnailImage']
            #     signalData = {"type": "mainVideoProgressUpdate","data": videoDetailsD}
            # elif inst.isDefault == 3:
            #     signalData = {"type": "mainVideoProgressUpdate","data":  {"id": str(inst.soloCampaign.id),"status": 1,"completedPercentage": 100,"isDefault": inst.isDefault} }
            # elif inst.isDefault == 4:
            #     groupCampaign = inst.groupCampaign.groupcampaign
            #     data = {"id": str(groupCampaign.id),"totalData": groupCampaign.totalData,"campaign": str(groupCampaign.campaign.id),"isGenerated": groupCampaign.isGenerated,"isDefault": inst.isDefault}
            #     allQuery = GroupSingleCampaign.objects.filter(groupcampaign=data['id'])
            #     count = allQuery.filter(genVideo__status=1).count()
            #     if not groupCampaign.isAdded:
            #         data['completed'] = 0
            #     else:
            #         data['completed'] = count

            #     if not groupCampaign.isGenerated:
            #         if allQuery.filter(genVideo__status=2).count()==0:
            #             groupCampaign.isGenerated = True
            #             groupCampaign.save()
            #             data['isGenerated'] = True
            #     signalData = {"type": "mainVideoProgressUpdate","data": data}
            # else:
            #     #signalData = {"type": "mainVideoProgressUpdate","data":  {"id": inst.id,"status": 1,"completedPercentage": 100,"isDefault": inst.isDefault} }
            #     return 0
            # channel_layer = get_channel_layer()
            # async_to_sync(channel_layer.group_send)(
            #     str(inst.multipleScene.user.id),
            #     {
            #         "type": "sendSignals",
            #         "text": signalData,
            #     },
            # )

            # if inst.isDefault == 1 or inst.isDefault == 2:
            #     vinst = VideoCreditUsage(usedCredit=ceil(inst.totalFrames/(settings.VIDEOCREDIT_RATE*60)),user=inst.multipleScene.user,usedCreditType=0,name=inst.multipleScene.name,info=json.dumps({'gid': [inst.id]}))
            #     vinst.save()
            # elif inst.isDefault == 3:
            #     vinst = VideoCreditUsage(usedCredit=ceil(inst.totalFrames/(settings.VIDEOCREDIT_RATE*60)),user=inst.multipleScene.user,usedCreditType=1,name=inst.soloCampaign.campaign.name,info=json.dumps({'gid': [inst.id],'type': 'solo','id': str(inst.soloCampaign.id)}))
            #     vinst.save()
            # elif inst.isDefault == 4:
            #     #vinst,cr = VideoCreditUsage.get_or_create(usedCredit=ceil(inst.totalFrames/settings.VIDEOCREDIT_RATE),user=inst.multipleScene.user,usedCreditType=1,name=inst.groupCampaign.groupcampaign.campaign.name,info=json.dumps({'gid': totalgid,'type': 'group','id': inst.id}))
            #     #inst.save()

            #     t = Thread(target=sendGroupCampaignEmail,args=(inst.groupCampaign,))
            #     t.start()
            # return 0
        
        elif mainData["type"] == "videoCreateSnapshot":
            inst = SnapshotUrl.objects.get(id=mainData["id"])
            signalData = {"type": "videoCreateSnapshot","data":  {"id": inst.id,"url": inst.url,"image": settings.BASE_URL + inst.image.url} }
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(mainData["user"]),
                {
                    "type": "sendSignals",
                    "text": signalData,
                },
            )
        elif mainData["type"] == "fabricJsonToImage":
            inst = MainThumbnail.objects.get(id=mainData["id"])
            signalData = {"type": "fabricJsonToImage","data":  {"id": inst.id,"thumbnailImage": settings.BASE_URL + inst.thumbnailImage.url,"name": inst.name} }
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(mainData["user"]),
                {
                    "type": "sendSignals",
                    "text": signalData,
                },
            )

    # Function to disconnet the Socket
    def disconnect(self, close_code):
        self.close()
        # pass

    # Custom Notify Function which can be called from Views or api to send message to the frontend
    def setThumbnail(self, event):
        self.send(text_data=json.dumps(event["text"]))