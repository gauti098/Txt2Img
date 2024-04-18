import json
from rest_framework import serializers
from django.conf import settings
from aiQueueManager.models import (
    AiTask,MergeTag,
    VideoRenderMultipleScene,
    VideoRenderSingleScene,
    GeneratedFinalVideo,SnapshotUrl,VideoThemeTemplate,
    VideoGradientColor
)

from videoThumbnail.serializers import MainThumbnailListSerializer
from videoThumbnail.models import MainThumbnail

class AiTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = AiTask
        fields = '__all__'

class SnapshotUrlSerializer(serializers.ModelSerializer):

    class Meta:
        model = SnapshotUrl
        fields = ('id','url','image',)

    def to_representation(self, instance):
        data = super(SnapshotUrlSerializer, self).to_representation(instance)
        url = data['url']
        if url[0]=='$':
            data['isMergeTag']= True
        else:
            data['isMergeTag']= False
        return data



class VideoThemeTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = VideoThemeTemplate
        fields = ('id','name','thumbnail','filePreview','config')

    def to_representation(self, instance):
        data = super(VideoThemeTemplateSerializer, self).to_representation(instance)

        if data['config']:
            try:
                data['config'] = json.loads(data['config'])
            except Exception as e:
                data['config'] = f"Can't Load config Data. Error:- {str(e)}"
        return data



class VideoGradientColorSerializer(serializers.ModelSerializer):
    ctg = serializers.ReadOnlyField(default=3)

    class Meta:
        model = VideoGradientColor
        fields = ('id','name','media_file','media_thumbnail','ctg')




import string
class MergeTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = MergeTag
        fields = ('id','name','value',)

    def create(self, validated_data):
        name = validated_data.pop('name')
        if name[:2] == "{{" and name[-2:] == "}}":
            name = name[2:-2]
        elif name[0] == '{' and name[-1] == '}':
            name = name[1:-1]
        allowedChar = [ii for ii in string.ascii_uppercase + string.ascii_lowercase + string.digits + " -_,.;:()*%$#@!~`"]
        for ii in name:
            if ii not in allowedChar:
                raise serializers.ValidationError({'name': ['Only " -_,.;:()*%$#@!~`" Special Character are Allowed.']})
        value = validated_data.pop('value')
        user = validated_data.pop('user')

        curntMTag = "{{"+name+"}}"
        totalTag = settings.DEFAULT_MERGE_TAG + settings.SPECIAL_MERGE_TAG
        if curntMTag not in totalTag:
            try:
                mainInst,ct = MergeTag.objects.get_or_create(name=curntMTag,value=value,user=user)
                return mainInst
            except:
                raise serializers.ValidationError({'name': ["This Field Already Exist."]})
        else:
            raise serializers.ValidationError({'name': ["This Field Already Exist as Special Tag."]})
        


class VideoRenderSingleSceneSerializer(serializers.ModelSerializer):

    #textAnimation = VideoTextTemplateDataSerializer(required=False)
    #snapshotData = SnapshotUrlSerializer(required=False)

    class Meta:
        model = VideoRenderSingleScene
        fields = ('id','text','videoThemeTemplate','videoThemeTemplateData','bgVideoType','bgVideoID','bgColor','isSnapshotMergeTag','snapshotData','prsCategory','prsPosition','prsBgType','prsBgImageId','prsBgColor','isLogo','logo','isMusic','music',)

    def to_representation(self, instance):
        data = super(VideoRenderSingleSceneSerializer, self).to_representation(instance)
        if data['snapshotData']:
            t = SnapshotUrl.objects.get(id=data['snapshotData'])
            try:
                req = self.context['request']
            except:
                req = None
            data['snapshotData'] = SnapshotUrlSerializer(t,context={'request': req}).data
        if data['videoThemeTemplateData']:
            try:
                data['videoThemeTemplateData'] = json.loads(data['videoThemeTemplateData'])
            except Exception as e:
                data['videoThemeTemplateData'] = {'color': []}
        return data

        '''else:
            data['isTextAnimation'] = False
        if data['logo']:
            data['isLogo'] = True
        else:
            data['isLogo'] = True
        if data['music']:
            data['isMusic'] = True
        else:
            data['isMusic'] = True'''
        return data


class VideoRenderMultipleSceneSerializer(serializers.ModelSerializer):
    #colors = ColorsSerializer(many=True)
    #mergeTag = MergeTagSerializer(many=True)
    singleScene = VideoRenderSingleSceneSerializer(many=True)

    class Meta:
        model = VideoRenderMultipleScene
        fields = ('id','name','avatar_image','avatar_sound','singleScene','thumbnailImage','timestamp')
        extra_kwargs = {
            'thumbnailImage': {'read_only': True},
            'timestamp': {'read_only': True},
        }

    def to_representation(self, instance):
        data = super(VideoRenderMultipleSceneSerializer, self).to_representation(instance)
        mergeId = data.pop('singleScene')
        return data

    def create(self, validated_data):

        name = validated_data.pop('name')
        user = validated_data.pop('user')

        avatar_image = validated_data.pop('avatar_image')
        avatar_sound = validated_data.pop('avatar_sound')

        singleScene = validated_data.pop('singleScene')
        
        mainInst = VideoRenderMultipleScene.objects.create(user=user,name=name,avatar_image=avatar_image,avatar_sound=avatar_sound)

        for data in singleScene:
            tempInst = VideoRenderSingleScene.objects.create(**data)
            mainInst.singleScene.add(tempInst)

        return mainInst





class GenerateFinalVideoSerializer(serializers.ModelSerializer):
    #multipleScene = VideoRenderMultipleSceneSerializer()

    class Meta:
        model = GeneratedFinalVideo
        fields = ('id','name','status','video','timestamp','multipleScene','thumbnailImage')

    def to_representation(self, instance):
        sdata = super(GenerateFinalVideoSerializer, self).to_representation(instance)

        if instance.isDefault!=2:
            sdata['name'] = instance.multipleScene.name
            sdata['id'] = instance.multipleScene.id
        if sdata['status']==3 or sdata['status']==4:
            sdata['status'] = 3
        sdata['completedPercentage'] = instance.getApproxPercentage()
        sdata['totalDuration'] = 100
        sdata['approxTime'] = 100
        return sdata



class VideoDetailsSerializer(serializers.ModelSerializer):
    generateStatus = GenerateFinalVideoSerializer()
    sceneThumbnails = MainThumbnailListSerializer(many=True)
    selectedThumbnail = MainThumbnailListSerializer()

    class Meta:
        model = VideoRenderMultipleScene
        fields = ('id','name','thumbnailImage','descriptions','generateStatus','sceneThumbnails','selectedThumbnail','tags','timestamp','updated', )
        extra_kwargs = {
            'thumbnailImage': {'read_only': True},
            'timestamp': {'read_only': True},
            'updated': {'read_only': True},
        }

    def to_representation(self, instance):
        data = super(VideoDetailsSerializer, self).to_representation(instance)
        data['thumbnailImage'] = data['generateStatus']['thumbnailImage']
        if instance.generateStatus:
            data['video'] = data['generateStatus']['video']
        
        if not data['selectedThumbnail']:
            _inst = MainThumbnail.objects.filter(isPublic=True,category=1).first()
            instance.selectedThumbnail = _inst
            instance.save()
            data['selectedThumbnail'] = MainThumbnailListSerializer(_inst,context={'request': self.context['request']}).data
        data.pop('generateStatus')
        return data