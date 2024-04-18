from rest_framework import serializers
from django.contrib.auth import get_user_model

from salesPage.models import (
    SalesPageEditor,TextEditor,
    ImageEditor,ButtonEditor,
    IconEditor,VideoEditor,ButtonDataEditor,
    CrouselEditor,SalesPageDetails,
)

from aiQueueManager.models import MergeTag
from userlibrary.serializers import (
    FileUploadSerializer
)
import json


class SalesPageListSerializer(serializers.ModelSerializer):

    class Meta:
        model = SalesPageEditor
        fields = ('id','name','previewImage','timestamp','updated','isPersonalized','isPublish','isDefault')



class SalesPagePublicListSerializer(serializers.ModelSerializer):

    class Meta:
        model = SalesPageEditor
        fields = ('id','name','previewImage','mobileViewPreview','desktopViewPreview','timestamp','updated','isPublish')


class SalesPageDetailsSerializer(serializers.ModelSerializer):
    favicon = FileUploadSerializer(read_only=True)

    class Meta:
        model = SalesPageDetails
        fields = ('salesPage','pageLink','favicon')
        extra_kwargs = {
            'salesPage': {'read_only': True}
        }



class TextEditorSerializer(serializers.ModelSerializer):

    class Meta:
        model = TextEditor
        fields = '__all__'

class ImageEditorSerializer(serializers.ModelSerializer):

    class Meta:
        model = ImageEditor
        fields = '__all__'

class ButtonEditorSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ButtonEditor
        fields = '__all__'

class IconEditorSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = IconEditor
        fields = '__all__'

class VideoEditorSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = VideoEditor
        fields = ('id','height','isDeleted')

class CrouselEditorSerializer(serializers.ModelSerializer):
    
    crouselData = FileUploadSerializer(read_only=True, many=True)

    class Meta:
        model = CrouselEditor
        fields = ('id','crouselData','isDeleted')
    


class ButtonDataEditorSerializer(serializers.ModelSerializer):
    
    buttonData = ButtonEditorSerializer(many=True)

    class Meta:
        model = ButtonDataEditor
        fields = ('id','buttonData','isDeleted')

    def create(self, validated_data):
        buttonData = validated_data.pop('buttonData')
        inst = ButtonDataEditor.objects.create()
        for temp in buttonData:
            inst.buttonData.add(ButtonEditor.objects.create(**temp))
        inst.save()
        return inst

class SalesPageEditorSerializer(serializers.ModelSerializer):
    
    textEditor = TextEditorSerializer(many=True)
    imageEditor = ImageEditorSerializer(many=True)
    buttonEditor = ButtonDataEditorSerializer(many=True)
    iconEditor = IconEditorSerializer(many=True)
    videoEditor = VideoEditorSerializer(many=True)
    crouselEditor = CrouselEditorSerializer(read_only=True,many=True)
    
    class Meta:
        model = SalesPageEditor
        fields = ('id','name', 'textEditor','imageEditor','buttonEditor','iconEditor','videoEditor','crouselEditor','themeColorConfig','publicId','isPublish')
        extra_kwargs = {
            'publicId': {'read_only': True}
        }
    
    def create(self, validated_data):

        name = validated_data.pop('name')
        themeColorConfig = validated_data.pop('themeColorConfig')
        user = validated_data.pop('user')

        textEditor = validated_data.pop('textEditor')
        imageEditor = validated_data.pop('imageEditor')
        iconEditor = validated_data.pop('iconEditor')
        buttonEditor = validated_data.pop('buttonEditor')
        videoEditor = validated_data.pop('videoEditor')
        isPublish = validated_data.pop('isPublish')
        
        mainInst = SalesPageEditor.objects.create(user=user,name=name,themeColorConfig=themeColorConfig,isPublish=isPublish)

        for data in textEditor:
            tempInst = TextEditor.objects.create(**data)
            mainInst.textEditor.add(tempInst)

        for data in imageEditor:
            tempInst = ImageEditor.objects.create(**data)
            mainInst.imageEditor.add(tempInst)

        for data in iconEditor:
            tempInst = IconEditor.objects.create(**data)
            mainInst.iconEditor.add(tempInst)

        for data in videoEditor:
            tempInst = VideoEditor.objects.create(**data)
            mainInst.videoEditor.add(tempInst)

        for data in buttonEditor:
            serializerInst = ButtonDataEditorSerializer(data=data)
            if serializerInst.is_valid():
                serializerInst = serializerInst.save()
                mainInst.buttonEditor.add(serializerInst)
        return mainInst



    def to_representation(self, instance):
        data = super(SalesPageEditorSerializer, self).to_representation(instance)
        
        try:
            data['themeColorConfig'] = json.loads(data['themeColorConfig'])
        except:
            data['themeColorConfig'] = {'colors': {}}

        ## add public default config
        inst = SalesPageEditor.objects.filter(publicId = data['publicId'],isPublic=True)
        if inst:
            try:
                data['publicThemeColorCofig'] = json.loads(inst.first().themeColorConfig)
            except:
                data['publicThemeColorCofig'] = {'colors': {}}
        else:
            data['publicThemeColorCofig'] = {'colors': {}}

        

        for cindx,inst in enumerate(instance.crouselEditor.all()):
            prevData = data['crouselEditor'][cindx]['crouselData']
            if inst.orderId:
                newOrderData = [0]*len(prevData)
                newOrder = inst.get_order()
                for ti,tinst in enumerate(prevData):
                    newOrderData[newOrder[str(tinst['id'])]]=tinst
                data['crouselEditor'][cindx]['crouselData'] = newOrderData
            # else:
            #     print('No order Id')
        return data
