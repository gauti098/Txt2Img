from django.conf import settings
from rest_framework import serializers
import json
import logging
import traceback
from campaign import serializers as campaignSerializers
logger = logging.getLogger(__name__)

from newImageEditor.models import (
    ImageCreator,ImageCreatorGenerated,
    IMAGECREATORGENERATED_UUID_TOTAL_NO
)

class ImageCreatorMinSerializer(serializers.ModelSerializer):

    class Meta:
        model = ImageCreator
        fields = ("id","name","isGenerated","isPersonalized")


class ImageCreatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = ImageCreator
        fields = ("id","name","isGenerated","isPersonalized","thumbnail","timestamp")



class ImageCreatorDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ImageCreator
        fields = ("id","name","isGenerated","isPersonalized","jsonData","timestamp")

    # def to_representation(self, instance):
    #     data = super(ImageCreatorDetailsSerializer, self).to_representation(instance)

    #     try:
    #         data['jsonData'] = json.loads(data["jsonData"])
    #     except Exception as e:
    #         logger.error(f"Unable To Parse TempVideoCreatorDetailsSerializer: {e}" )
    #     return data

from campaign import models as campaignModels
from base64 import b64encode

class ImageCreatorDetailSerializer(serializers.ModelSerializer):
    mailClient = campaignSerializers.EmailClientSerializer()

    class Meta:
        model = ImageCreator
        fields = ("id","name","thumbnail","isGenerated","redirectUrl",'mailClient',"isPersonalized","timestamp")

    def to_representation(self, instance):
        data = super(ImageCreatorDetailSerializer, self).to_representation(instance)
        _thumbnailUrl =  f"https://autovid.ai/i/{instance.slug}?v=" #f'{settings.BASE_URL}/api/newimage/image/rt-generate/?uid={instance._uid}'
        tagTypeMapping = {"text": 0,"url": 1,"email": 2}
        try:
            data["mergeTag"] = json.loads(instance.mergeTag)
            for ii,_tag in enumerate(data["mergeTag"]):
                if ii!=0:
                    _thumbnailUrl += f'||{_tag[0]}'
                else:
                    _thumbnailUrl += f'{_tag[0]}'
        except:
            pass

        if instance.mailClient:
            data["code"] = instance.mailClient.getImageCode(_thumbnailUrl,data["redirectUrl"],splited=False) #,"data["redirectUrl"]")
        else:
            data["code"] = campaignModels.EmailClient.getImageCode(_thumbnailUrl,data["redirectUrl"],splited=False) #,data["redirectUrl"])
        data["thumbnailUrl"] = _thumbnailUrl
        
        _uid = f'{instance._uid}'[:IMAGECREATORGENERATED_UUID_TOTAL_NO] + str(b64encode(bytes(str(instance.id),'utf-8')),'utf-8')
        data['link'] = f"https://autovid.ai/i/{_uid}?type=1"
        data["imageSoloGenCount"] = ImageCreatorGenerated.objects.filter(generationType=1,imageCreator=instance).count()
        return data


class ImageCreatorSoloLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = ImageCreatorGenerated
        fields = ('id','thumbnail','mergeTagValue','isGenerated','timestamp')

    def to_representation(self, instance):
        data = super(ImageCreatorSoloLinkSerializer,self).to_representation(instance)
        _uid = f'{instance._uid}'[:IMAGECREATORGENERATED_UUID_TOTAL_NO] + str(b64encode(bytes(str(instance.id),'utf-8')),'utf-8')
        data['thumbnail'] = f"https://autovid.ai/i/{_uid}"
        try:
            data['mergeTagValue'] = json.loads(data["mergeTagValue"])
        except:
            pass
        try:
            data['mergeTag'] = json.loads(instance.imageCreator.mergeTag)
        except:
            pass
        return data
