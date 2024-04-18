from channels.generic.websocket import WebsocketConsumer
import json
from asgiref.sync import async_to_sync

import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer




class NotificationConsumer(WebsocketConsumer):

    def connect(self):
        if self.scope["user"].is_anonymous:
            self.accept()
            self.send(json.dumps({'message': 'Token is Not Valid'}))
            self.close()
        else:
            self.group_name = str(self.scope["user"].pk)  # Setting the group name as the pk of the user primary key as it is unique to each user. The group name is used to communicate with the user.
            async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
            self.accept()
            _name = self.scope['user'].email
            self.send(json.dumps({"command": "welcome","message": f"Hi, {_name}. Welcome To AutoVid.AI"}))
        
    
    def receive(self,text_data):
        print(text_data)

    # Function to disconnet the Socket
    def disconnect(self, close_code):
        self.close()
        # pass

    # Custom Notify Function which can be called from Views or api to send message to the frontend
    def sendSignals(self, event):
        self.send(text_data=json.dumps(event["text"]))