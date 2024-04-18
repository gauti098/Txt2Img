from rest_framework import serializers
from django.contrib.auth import get_user_model

from userlibrary.models import FileUpload
import json




class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileUpload
        fields = ('id','name','media_type','media_file','fileInfo','media_thumbnail','category','timestamp','updated',)
        extra_kwargs = {
            'media_type': {'read_only': True},
            'timestamp': {'read_only': True},
            'updated': {'read_only': True},
            'fileInfo': {'read_only': True},
        }

    def to_representation(self, instance):
        data = super(FileUploadSerializer, self).to_representation(instance)
        if data['media_type'].split('/')[0] =='image':
            if not data['media_thumbnail']:
                data['media_thumbnail']= data['media_file']
        elif not (data['media_type'].split('/')[0] =='video' or data['media_type'] == "application/pdf"):
            data['media_thumbnail']= data['media_file']
        if data['category'] == 'aiVideo':
            data['video'] = data.pop('media_file')
            data['thumbnailImage'] = data.pop('media_thumbnail')
        elif data['category'] == 'upload':
            if data['media_type'].split('/')[0] =='video':
                data['bgType'] = 4
            if data['media_type'].split('/')[0] =='image':
                data['bgType'] = 2

        if data['fileInfo']:
            try:
                data['fileInfo'] = json.loads(data['fileInfo'])
            except:
                pass
        data['ctg'] = 2
        return data
