import json

from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.generic.websocket import WebsocketConsumer



class NewVideoCreatorConsumer(WebsocketConsumer):

    def connect(self):
        if self.scope["user"].is_anonymous:
            self.accept()
            self.send(json.dumps({'message': 'Token is Not Valid','status': 401}))
            #self.close()
        else:
            self.group_name = self.scope["user"].getWebsocketGroupName()  # Setting the group name as the pk of the user primary key as it is unique to each user. The group name is used to communicate with the user.
            async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
            self.accept()
            _name = self.scope['user'].email
            self.send(json.dumps({"command": "welcome",'message': f'{self.group_name} : {self.channel_name}'}))
            self.send(json.dumps({"command": "welcome","message": f"Hi, {_name}. Welcome To AutoVid.AI"}))
            #self.sendWelcomeMessage(self.scope["user"])

            
    def receive(self,text_data):
        mainData = json.loads(text_data)
        # if mainData["type"] == "sendToUser":
        #     _user = mainData.get("user",None)
        #     if _user:
        #         channel_layer = get_channel_layer()
        #         async_to_sync(channel_layer.group_send)(
        #             str(_user),
        #             {
        #                 "type": "sendSignals",
        #                 "text": {"type": mainData["returnType"],"data": mainData["returnData"]},
        #             },
        #         )
    
        # elif mainData["type"] == "videoCreateSnapshot":
        #     inst = SnapshotUrl.objects.get(id=mainData["id"])
        #     signalData = {"type": "videoCreateSnapshot","data":  {"id": inst.id,"url": inst.url,"image": settings.BASE_URL + inst.image.url} }
        #     channel_layer = get_channel_layer()
        #     async_to_sync(channel_layer.group_send)(
        #         str(mainData["user"]),
        #         {
        #             "type": "sendSignals",
        #             "text": signalData,
        #         },
        #     )
        # elif mainData["type"] == "fabricJsonToImage":
        #     inst = MainThumbnail.objects.get(id=mainData["id"])
        #     signalData = {"type": "fabricJsonToImage","data":  {"id": inst.id,"thumbnailImage": settings.BASE_URL + inst.thumbnailImage.url,"name": inst.name} }
        #     channel_layer = get_channel_layer()
        #     async_to_sync(channel_layer.group_send)(
        #         str(mainData["user"]),
        #         {
        #             "type": "sendSignals",
        #             "text": signalData,
        #         },
        #     )

    # Function to disconnet the Socket
    def disconnect(self, close_code):
        self.close()
        # pass

    def sendWelcomeMessage(self,user):
        channel_layer = get_channel_layer()
        # {"command": "sharingPage.add","result":  {"id": inst.id,"thumbnailImage": settings.BASE_URL + inst.thumbnailImage.url,"name": inst.name} }
        async_to_sync(channel_layer.group_send)(
            user.getWebsocketGroupName(),
            {
                "type": "sendCommand",
                "text": {"command": "welcome.message","message": f"Hi, {user.name}. Welcome To AutoVid.AI"},
            },
        )

    # Custom Notify Function which can be called from Views or api to send message to the frontend
    def sendCommand(self, event):
        self.send(text_data=json.dumps(event["text"]))