from rest_framework import serializers
import json
import logging
import traceback
from campaign import models as campaignModels
from campaign.serializers import EmailClientSerializer
from newImageEditor.models import ImageCreator
from newImageEditor.serializers import ImageCreatorSerializer
from django.conf import settings
logger = logging.getLogger(__name__)

from newVideoCreator import models as newVideoCreatorModels

from salesPage.serializers import SalesPageListSerializer

class FontConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.FontConfig
        fields = ("fontUrl",)

    def to_representation(self, instance):
        data = super(FontConfigSerializer,self).to_representation(instance)
        data['fontConfig'] = {"style": newVideoCreatorModels.FONT_STYLE_DICT[instance.style],"weight": newVideoCreatorModels.FONT_WEIGHT_DICT[instance.weight]}
        return data


class FontFamilySerializer(serializers.ModelSerializer):
    #fonts = FontConfigSerializer(many=True)

    class Meta:
        model = newVideoCreatorModels.FontFamily
        fields = ("name",)


class MainVideoGenerateSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.MainVideoGenerate
        fields = ('id','videoCreator','video','status','progress','timestamp')


class MainVideoGenerateForCampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.MainVideoGenerate
        fields = ('video','thumbnail',)
    
    def to_representation(self, instance):
        data = super(MainVideoGenerateForCampaignSerializer,self).to_representation(instance)
        if instance.generationType==0:
            if instance.videoCreator.thumbnailInst:
                if instance.videoCreator.thumbnailInst.thumbnail:
                    data["thumbnail"] = instance.videoCreator.thumbnailInst.thumbnail.url
        return data


class BatchVideoGenerateForCampaignSerializer(serializers.ModelSerializer):

    thumbnailInst = ImageCreatorSerializer()
    
    class Meta:
        model = newVideoCreatorModels.GroupHandler
        fields = ('thumbnailInst',)

    def to_representation(self, instance):
        data = super(BatchVideoGenerateForCampaignSerializer,self).to_representation(instance)
        _thumbnailInst = data.pop("thumbnailInst")
        data["video"] = None
        if instance.videoCreator.mainVideoGenerate:
            if instance.videoCreator.mainVideoGenerate.video:
                data["video"] = instance.videoCreator.mainVideoGenerate.video.url
        data["thumbnailImage"] = _thumbnailInst.get("thumbnail",None)
        
        return data


class MainVideoGenerateWithMergeTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.MainVideoGenerate
        fields = ('id','video','thumbnail','mergeTagValue',"allMergeTag",'status','progress','timestamp')

    def to_representation(self, instance):
        data = super(MainVideoGenerateWithMergeTagSerializer,self).to_representation(instance)
        try:
            data['mergeTagValue'] = json.loads(data["mergeTagValue"])
        except:
            pass
        try:
            data['allMergeTag'] = json.loads(data["allMergeTag"])
        except:
            pass
        return data

    
class MainVideoGenerateCampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.MainVideoGenerate
        fields = ('id','video','thumbnail','mergeTagValue',"allMergeTag",'status','progress','timestamp')

    def to_representation(self, instance):
        data = super(MainVideoGenerateCampaignSerializer,self).to_representation(instance)
        try:
            data['mergeTagValue'] = json.loads(data["mergeTagValue"])
        except:
            pass
        try:
            data['allMergeTag'] = json.loads(data["allMergeTag"])
        except:
            pass

        data["campaignUrl"] = f"https://autovid.ai/p/{instance.videoCreator.slug}/{instance.uniqueIdentity}"
        # if instance._shortUrl:
        #     #data["campaignUrl"] = instance._shortUrl.getUrl()
        #     data["campaignUrl"] = f"https://autovid.ai/p/{instance.videoCreator.slug}/{instance.uniqueIdentity}"
        # else:
        #     data["campaignUrl"] = f"https://autovid.ai/p/{data['id']}?email=video_creator"
        return data
    
class MainVideoGenerateSoloMailSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.MainVideoGenerate
        fields = ('id','video','thumbnail','mergeTagValue',"allMergeTag",'status','progress','timestamp')

    def to_representation(self, instance):
        data = super(MainVideoGenerateSoloMailSerializer,self).to_representation(instance)
        try:
            data['mergeTagValue'] = json.loads(data["mergeTagValue"])
        except:
            pass
        try:
            data['allMergeTag'] = json.loads(data["allMergeTag"])
        except:
            pass

        data["campaignUrl"] = f"https://autovid.ai/p/{instance.videoCreator.slug}/{instance.uniqueIdentity}"

        # if instance._shortUrl:
        #     #data["campaignUrl"] = instance._shortUrl.getUrl()
        #     data["campaignUrl"] = f"https://autovid.ai/p/{instance.videoCreator.slug}/{instance.uniqueIdentity}"
        # else:
        #     data["campaignUrl"] = f"https://autovid.ai/p/{data['id']}?email=video_creator"

        try:
            if instance.videoCreator.mailClient:
                data["code"] = instance.videoCreator.mailClient.getCode(instance.videoCreator.slug,instance.uniqueIdentity,newLink=True)
            else:
                data["code"] = campaignModels.EmailClient.getCode(None,instance.videoCreator.slug,instance.uniqueIdentity,newLink=True)
        except:
            data["code"] = campaignModels.EmailClient.getCode(None,instance.videoCreator.slug,instance.uniqueIdentity,newLink=True)
        # try:
        #     if instance.videoCreator.mailClient:
        #         data["code"] = instance.videoCreator.mailClient.getCode(data['id'],"video_creator")
        #     else:
        #         data["code"] = campaignModels.EmailClient.getCode(None,data["id"],"video_creator")
        # except:
        #     data["code"] = campaignModels.EmailClient.getCode(None,data["id"],"video_creator")
        return data


class BatchMailMinSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.GroupHandler
        fields = ('id','fileName','isAdded','status','totalCount','generatedCount',"timestamp")

    def to_representation(self, instance):
        data = super(BatchMailMinSerializer,self).to_representation(instance)
        data["progress"] = int((data["generatedCount"]/data["totalCount"])*100)

        data["previewUrl"] = f"https://autovid.ai/p/{data['id']}/"
        # if instance._shortUrl:
        #     data["previewUrl"] = instance._shortUrl.getUrl()
        #     slug = instance._shortUrl.slug
        #     newLink = True
        # else:
        #     data["previewUrl"] = f"https://autovid.ai/p/{data['id']}?email=campaign_test__batch__"

        try:
            _mcInst = campaignModels.EmailClient.objects.get(id=instance.mailClient)
            data["code"] = _mcInst.getCode(instance.videoCreator.slug,newLink=True)
        except:
            data["code"] = campaignModels.EmailClient.getCode(None,instance.videoCreator.slug,newLink=True)
        
        return data


class VideoCreatorSerializer(serializers.ModelSerializer):
    mainVideoGenerate = MainVideoGenerateSerializer()

    class Meta:
        model = newVideoCreatorModels.TempVideoCreator
        fields = ("id","name","isPersonalized","mainVideoGenerate","thumbnail","timestamp","updated")


class VideoSceneSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.AiVideoSceneGenerate
        fields = ("sceneIndex","video","thumbnail",)


class VideoHorizontalTemplateSerializer(serializers.ModelSerializer):
    hVideo = VideoCreatorSerializer()

    class Meta:
        model = newVideoCreatorModels.VideoTemplate
        fields = ("id","name","hVideo",)

    def to_representation(self, instance):
        data = super(VideoHorizontalTemplateSerializer,self).to_representation(instance)
        _tmp = data.pop('hVideo')
        data['id']=_tmp["id"]
        data['thumbnail'] = _tmp["thumbnail"]
        data['video'] = None
        data['scenes'] = []
        if instance.hVideo.mainVideoGenerate:
            data['video'] = _tmp["mainVideoGenerate"]["video"]
            allScene = instance.hVideo.mainVideoGenerate.aiSceneGenerate.all()
            data['scenes'] = VideoSceneSerializer(allScene,many=True,context={'request': self.context['request']}).data

        return data

class VideoVerticalTemplateSerializer(serializers.ModelSerializer):
    vVideo = VideoCreatorSerializer()

    class Meta:
        model = newVideoCreatorModels.VideoTemplate
        fields = ("id","name","vVideo",)

    def to_representation(self, instance):
        data = super(VideoVerticalTemplateSerializer,self).to_representation(instance)
        _tmp = data.pop('vVideo')
        data['id']=_tmp["id"]
        data['thumbnail'] = _tmp["thumbnail"]
        data['video'] = None
        data['scenes'] = []
        if instance.vVideo.mainVideoGenerate:
            data['video'] = _tmp["mainVideoGenerate"]["video"]
            allScene = instance.vVideo.mainVideoGenerate.aiSceneGenerate.all()
            data['scenes'] = VideoSceneSerializer(allScene,many=True,context={'request': self.context['request']}).data
        return data

class VideoSquareTemplateSerializer(serializers.ModelSerializer):
    sVideo = VideoCreatorSerializer()

    class Meta:
        model = newVideoCreatorModels.VideoTemplate
        fields = ("id","name","sVideo")

    def to_representation(self, instance):
        data = super(VideoSquareTemplateSerializer,self).to_representation(instance)
        _tmp = data.pop('sVideo')
        data['id']=_tmp["id"]
        data['thumbnail'] = _tmp["thumbnail"]
        data['video'] = None
        data['scenes'] = []
        if instance.sVideo.mainVideoGenerate:
            data['video'] = _tmp["mainVideoGenerate"]["video"]
            allScene = instance.sVideo.mainVideoGenerate.aiSceneGenerate.all()
            data['scenes'] = VideoSceneSerializer(allScene,many=True,context={'request': self.context['request']}).data

        return data


class VideoTemplateSerializer(serializers.ModelSerializer):
    hVideo = VideoCreatorSerializer()
    vVideo = VideoCreatorSerializer()
    sVideo = VideoCreatorSerializer()

    class Meta:
        model = newVideoCreatorModels.VideoTemplate
        fields = ("id","name","hVideo","vVideo","sVideo")


class TempVideoCreatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.TempVideoCreator
        fields = ("id","name")
        

class BatchGeneratedHistoryFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.GroupHandler
        fields = ("id","generatedFile")
        

class EmailGenerateHistorySerializer(serializers.ModelSerializer):
    soloInst = MainVideoGenerateSoloMailSerializer()
    groupInst = BatchMailMinSerializer()

    class Meta:
        model = newVideoCreatorModels.EmailGenTracker
        fields = ("id","soloInst","groupInst")

    def to_representation(self, instance):
        data = super(EmailGenerateHistorySerializer,self).to_representation(instance)
        if instance._type==0:
            data.pop("groupInst")
            data = data.pop("soloInst")
        else:
            data.pop("soloInst")
            data = data.pop("groupInst")
        data["type"] = instance._type
        return data


# class BatchMailDetailsSerializer(serializers.ModelSerializer):
    
#     class Meta:
#         model = newVideoCreatorModels.MainVideoGenerate
#         fields = ("id","status",)

#     def to_representation(self, instance):
#         data = super(BatchMailDetailsSerializer, self).to_representation(instance)
#         _value = json.loads(instance.mergeTagValue)
#         _key = json.loads(instance.allMergeTag)
#         data['isGenerated'] = False
#         data['tableData'] = mainD
#         data['tableData']['campaignLink'] = None
#         if instance.genVideo:
#             data['isGenerated'] = instance.genVideo.status
#             if data['isGenerated'] == 1:
#                 data['tableData']['campaignLink'] = instance.getShortUrl()#f"{settings.FRONTEND_URL}/preview/{data['groupcampaign']}/?email={data['uniqueIdentity']}"

#         return data



class VideoDetailsSerializer(serializers.ModelSerializer):

    mainVideoGenerate = MainVideoGenerateSerializer()
    sharingPage = SalesPageListSerializer()
    mailClient = EmailClientSerializer()
    thumbnailInst = ImageCreatorSerializer()

    class Meta:
        model = newVideoCreatorModels.TempVideoCreator
        fields = ("id","name","isPersonalized","mainVideoGenerate","thumbnail","thumbnailType","thumbnailInst","sharingPage","mailClient","timestamp","updated")

    def to_representation(self, instance):
        data = super(VideoDetailsSerializer,self).to_representation(instance)
        data["mergeTag"] = json.loads(instance.mergeTag)
        data["allMergeTag"] = json.loads(instance.allMergeTag)

        data["sceneThumbnails"] = []
        data['link'] = ""
        data["code"] = ""
        if instance.mainVideoGenerate:
            #allScene = instance.mainVideoGenerate.aiSceneGenerate.all()
            if instance.mainVideoGenerate.status==0:
                data['mainVideoGenerate']['message'] = "The video could not be generated. <br/>We are working to address the issue."
            allScene = ImageCreator.objects.filter(_videoId=data["id"])

            data["link"] = f"https://autovid.ai/p/{instance.slug}/{instance.mainVideoGenerate.uniqueIdentity}"
            # if instance.mainVideoGenerate._shortUrl:
            #     data["link"] = instance.mainVideoGenerate._shortUrl.getUrl()
            #     slug = instance.mainVideoGenerate._shortUrl.slug
            #     newLink=True
            #     uniqueIdentity = False
            # else:
            #     #data['link'] = f"https://autovid.ai/p/{instance.mainVideoGenerate.id}?email=video_creator"
            #     data["link"] = f"https://autovid.ai/p/{instance.slug}/{instance.mainVideoGenerate.uniqueIdentity}"
                

            
            if (not instance.isPersonalized) and instance.thumbnailInst:
                _pageUrl = f"https://autovid.ai/p/{instance.mainVideoGenerate.id}?email=nvc"
                _thumbnailUrl = f'{settings.BASE_URL}/api/newimage/image/rt-generate/?uid={instance.thumbnailInst._uid}'
                _rawTag = ""
                try:
                    for _tag in data["allMergeTag"]:
                        _rawTag += f'&{_tag[0]}_{_tag[1]}={_tag[0]}'
                except:
                    pass

                if instance.mailClient:
                    data["code"] = instance.mailClient.getImageCode(_thumbnailUrl + _rawTag,_pageUrl + _rawTag)
                else:
                    data["code"] = campaignModels.EmailClient.getImageCode(_thumbnailUrl + _rawTag,_pageUrl + _rawTag)
            else:
                if instance.mailClient:
                    data["code"] = instance.mailClient.getCode(instance.slug,instance.mainVideoGenerate.uniqueIdentity,newLink=True)
                else:
                    data["code"] = campaignModels.EmailClient.getCode(None,instance.slug,instance.mainVideoGenerate.uniqueIdentity,newLink=True)
                # if instance.mailClient:
                #     data["code"] = instance.mailClient.getCode(slug,uid = uniqueIdentity,newLink=newLink)
                # else:
                #     data["code"] = campaignModels.EmailClient.getCode(None,slug,uid = uniqueIdentity,newLink=newLink)




            data["sceneThumbnails"] = ImageCreatorSerializer(allScene,many=True,context={'request': self.context['request']}).data

        if data["thumbnailInst"]:
            data['thumbnailInst']["thumbnailType"] = data['thumbnailType']
        else:
            data["thumbnailInst"] = {"id":-1,"name":"Scene 1","personalized": -1,"thumbnailType": data['thumbnailType'],"thumbnail": data["thumbnail"]}
        
        data['downloadGenCount'] = newVideoCreatorModels.MainVideoGenerate.objects.filter(videoCreator=instance,generationType=1).count()
        data['sharingPageGenCount'] = newVideoCreatorModels.MainVideoGenerate.objects.filter(videoCreator=instance,generationType=2).count()
        data['batchMailGenCount'] = newVideoCreatorModels.EmailGenTracker.objects.filter(videoCreator=instance,_type=1).count()
        data['soloMailGenCount'] = newVideoCreatorModels.MainVideoGenerate.objects.filter(videoCreator=instance,generationType=4).count()

        data['report'] = {
            'linkClicked': 20,
            'videoPlayed': 15,
            'views': 11
        }
        
        
        return data

class TempVideoCreatorDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.TempVideoCreator
        fields = ("id","name","jsonData")

    def to_representation(self, instance):
        data = super(TempVideoCreatorDetailsSerializer, self).to_representation(instance)
        data['isGenerated'] = False
        if instance.mainVideoGenerate:
            data['isGenerated'] = True

        # try:
        #     data['jsonData'] = json.loads(data["jsonData"])
        # except Exception as e:
        #     logger.error(f"Unable To Parse TempVideoCreatorDetailsSerializer: {e}" )
        return data



class VideoAnimationSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.VideoAnimation
        fields = ("id","name","url",'exitSrc',"animationData")

    def to_representation(self, instance):
        data = super(VideoAnimationSerializer, self).to_representation(instance)
        try:
            if data['animationData']:
                data['animationData'] = json.loads(data["animationData"])
        except Exception as e:
            logger.error(f"Unable To Parse VideoAnimationSerializer: {e}" )
        data['src'] = data.pop('url')
        return data


class TextAnimationSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.TextAnimation
        fields = ("id","name","src","category","animationData")

    def to_representation(self, instance):
        data = super(TextAnimationSerializer, self).to_representation(instance)
        try:
            if data['animationData']:
                data['animationData'] = json.loads(data["animationData"])
        except Exception as e:
            logger.error(f"Unable To Parse VideoAnimationSerializer: {e}" )
        return data


class VideoSceneAnimationSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.VideoSceneAnimation
        fields = ("id","name","src","sample","category","animationData")

    def to_representation(self, instance):
        data = super(VideoSceneAnimationSerializer, self).to_representation(instance)
        try:
            if data['animationData']:
                data['animationData'] = json.loads(data["animationData"])
                # check if colors are present
                data['colors'] = data['animationData'].pop('colors',None)
        except Exception as e:
            logger.error(f"Unable To Parse VideoSceneAnimationSerializer: {e}" )
        # try:
        #     if data['colors']:
        #         data['colors'] = json.loads(data["colors"])
        # except Exception as e:
        #     logger.error(f"Unable To Parse VideoSceneAnimationSerializer: {e}" )
        return data



class VideoFilterSerializer(serializers.ModelSerializer):

    class Meta:
        model = newVideoCreatorModels.VideoFilter
        fields = ("id","name","url","data")

    def to_representation(self, instance):
        data = super(VideoFilterSerializer, self).to_representation(instance)
        try:
            if data['data']:
                data['data'] = json.loads(data["data"])
        except Exception as e:
            logger.error(f"Unable To Parse VideoFilterSerializer: {e}" )
        data['src'] = data.pop('url')
        return data