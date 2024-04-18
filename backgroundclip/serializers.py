from rest_framework import serializers

##my models
from backgroundclip.models import (
    APIVideoQuerySaver, ImageSearch,ImageApiRes,
    VideoApiRes,VideoSearch,
    APISaveVideo,APIVideoPopularSaver,
    APISaveImage,
    APIImagePopularSaver,
    APIImageQuerySaver
)
import json


class APISaveVideoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = APISaveVideo
        fields = ['id','previewVideo','fileInfo',"thumbnail","apiVideoInstType"]

    def to_representation(self, instance):
        data = super(APISaveVideoSerializer, self).to_representation(instance)
        data['media_file'] = data.pop('previewVideo')
        data['ctg'] = data.pop('apiVideoInstType')
        if data['fileInfo']:
            try:
                data['fileInfo'] = json.loads(data['fileInfo'])
            except:
                pass
        return data

class APISaveImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = APISaveImage
        fields = ['id','previewImage','image','fileInfo',]

    def to_representation(self, instance):
        data = super(APISaveImageSerializer, self).to_representation(instance)
        data['media_file'] = data.pop('previewImage')
        if data['fileInfo']:
            try:
                data['fileInfo'] = json.loads(data['fileInfo'])
            except:
                pass
        return data


class APISaveVideoServerSideSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = APISaveVideo
        fields = ['id','previewVideo','originalVideo','fileInfo','originalVideoFileInfo','thumbnail','isTransparent','isVideoProcessed','totalFrames',]

    def to_representation(self, instance):
        data = super(APISaveVideoServerSideSerializer, self).to_representation(instance)
        data['media_file'] = data.pop('originalVideo')
        data["imageSeqDir"] = instance.getImageSeqencePath(onlyDir=True)
        if data['fileInfo']:
            try:
                data['fileInfo'] = json.loads(data['fileInfo'])
            except:
                pass
        if data['originalVideoFileInfo']:
            try:
                data['originalVideoFileInfo'] = json.loads(data['originalVideoFileInfo'])
            except:
                pass
        return data


class ImageApiResSerializer(serializers.ModelSerializer):
    media_file = serializers.URLField(source='low_url')
    media_thumbnail = serializers.ReadOnlyField(default=None)
    bgType = serializers.ReadOnlyField(default=1)
    ctg = serializers.ReadOnlyField(default=0)

    class Meta:
        model = ImageApiRes
        fields = ['id','name','high_url','media_thumbnail','media_file','bgType','ctg',]


class VideoApiResSerializer(serializers.ModelSerializer):
    media_file = serializers.URLField(source='low_url')
    media_thumbnail = serializers.URLField(source='thumbnail')
    bgType = serializers.ReadOnlyField(default=3)

    class Meta:
        model = VideoApiRes
        fields = ['id','name','high_url','media_thumbnail','media_file','bgType']


class APIVideoSerializer(serializers.ModelSerializer):

    class Meta:
        model = APIVideoQuerySaver
        fields = ['id','name','thumbnail','fileInfo',"low_url"]

    def to_representation(self, instance):
        data = super(APIVideoSerializer, self).to_representation(instance)
        data['media_thumbnail'] = data.pop('thumbnail')
        data['media_file'] = data.pop('low_url')
        data['ctg'] = 0
        if data['fileInfo']:
            try:
                data['fileInfo'] = json.loads(data['fileInfo'])
            except:
                pass
        return data



class APIVideoPopularSerializer(serializers.ModelSerializer):

    class Meta:
        model = APIVideoPopularSaver
        fields = ['id','name','thumbnail','fileInfo',"low_url"]

    def to_representation(self, instance):
        data = super(APIVideoPopularSerializer, self).to_representation(instance)
        data['media_thumbnail'] = data.pop('thumbnail')
        data['media_file'] = data.pop('low_url')
        data['ctg'] = 1
        if data['fileInfo']:
            try:
                data['fileInfo'] = json.loads(data['fileInfo'])
            except:
                pass
        return data


class APIImagePopularSerializer(serializers.ModelSerializer):
    #media_thumbnail = serializers.URLField(source='low_url')
    media_file = serializers.URLField(source='low_url')
    ctg = serializers.ReadOnlyField(default=1)

    class Meta:
        model = APIImagePopularSaver
        fields = ['id','name','high_url','media_file','ctg']


class APIImageSerializer(serializers.ModelSerializer):
    #media_thumbnail = serializers.URLField(source='low_url')
    media_file = serializers.URLField(source='low_url')
    ctg = serializers.ReadOnlyField(default=0)

    class Meta:
        model = APIImageQuerySaver
        fields = ['id','name','high_url','media_file','ctg']

