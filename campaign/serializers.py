from django.conf import settings
from rest_framework import serializers

from campaign.models import (
    GroupSingleCampaign, MainCampaign,SoloCampaign,
    GroupCampaign,EmailClient
)
from userlibrary.serializers import FileUploadSerializer
import json
from aiQueueManager.serializers import VideoRenderMultipleSceneSerializer
from salesPage.serializers import SalesPageListSerializer
from videoThumbnail.serializers import MainThumbnailListSerializer
from videoThumbnail.models import MainThumbnail

from campaign.models import MAIL_CLIENT_CHOICES

MAIL_CLIENT_DATA = {}
for singleClient in MAIL_CLIENT_CHOICES:
    MAIL_CLIENT_DATA[singleClient[0]] = singleClient[1]


class MainCampaignCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = MainCampaign
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'thubmnailImage': {'read_only': True},
            'timestamp': {'read_only': True},
            'updated': {'read_only': True}
        }




class MainCampaignMinSerializer(serializers.ModelSerializer):

    class Meta:
        model = MainCampaign
        fields = ('id','name')


class EmailClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailClient
        fields = ('id','name','src')


class MainCampaignLinkedSerializer(serializers.ModelSerializer):

    class Meta:
        model = MainCampaign
        fields = ('id','name','tags','thubmnailImage')

class MainCampaignDetailsSerializer(serializers.ModelSerializer):

    video = VideoRenderMultipleSceneSerializer()
    salespage = SalesPageListSerializer()
    selectedThumbnail = MainThumbnailListSerializer()

    class Meta:
        model = MainCampaign
        fields = '__all__'
        extra_kwargs = {
            'selectedThumbnail': {'read_only': True},
            'thubmnailImage': {'read_only': True},
            'timestamp': {'read_only': True},
            'updated': {'read_only': True}
        }

    def to_representation(self, instance):
        data = super(MainCampaignDetailsSerializer, self).to_representation(instance)
        try:
            sceneThumbnails = MainThumbnailListSerializer(instance.video.sceneThumbnails.all(),many=True,context={'request': self.context['request']}).data
        except:
            sceneThumbnails = MainThumbnailListSerializer(instance.video.sceneThumbnails.all(),many=True).data
            for tmpI in sceneThumbnails:
                tmpI["thumbnailImage"] = settings.BASE_URL + tmpI["thumbnailImage"]
        data['sceneThumbnails'] = sceneThumbnails
        data['mailClient'] = MAIL_CLIENT_DATA
        if not data['selectedThumbnail']:
            _inst = MainThumbnail.objects.filter(isPublic=True,category=1).first()
            instance.selectedThumbnail = _inst
            instance.save()
            data['selectedThumbnail'] = MainThumbnailListSerializer(_inst,context={'request': self.context['request']}).data
        return data


class SoloCampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = SoloCampaign
        fields = ('id','uniqueIdentity','campaign','genVideo','data','timestamp')

    def to_representation(self, instance):
        data = super(SoloCampaignSerializer, self).to_representation(instance)
        data['campaignLink'] = instance.getShortUrl()
        try:
            data['completedPercentage'] = instance.genVideo.getApproxPercentage()
            data['totalDuration'] = 100
            data['approxTime'] = 100
            if instance.genVideo.status==3 or instance.genVideo.status==4:
                data['status'] = 3

            data['personalizedLength'] = len(json.loads(data['data']))
            data.pop('data')
            return data
        except:
            instance.delete()
            return []


class GroupSingleCampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = GroupSingleCampaign
        fields = ('id','uniqueIdentity','groupcampaign')

    def to_representation(self, instance):
        data = super(GroupSingleCampaignSerializer, self).to_representation(instance)
        mainD = json.loads(instance.data)
        data['isGenerated'] = False
        data['tableData'] = mainD
        data['tableData']['campaignLink'] = None
        if instance.genVideo:
            data['isGenerated'] = instance.genVideo.status
            if data['isGenerated'] == 1:
                data['tableData']['campaignLink'] = instance.getShortUrl()#f"{settings.FRONTEND_URL}/preview/{data['groupcampaign']}/?email={data['uniqueIdentity']}"
            
        return data


class GroupSingleCampaignDownloadSerializer(serializers.ModelSerializer):

    class Meta:
        model = GroupSingleCampaign
        fields = ('id','uniqueIdentity','groupcampaign')

    def to_representation(self, instance):
        data = super(GroupSingleCampaignDownloadSerializer, self).to_representation(instance)
        mainD = json.loads(instance.data)
        mainD['campaignLink'] = None
        if instance.genVideo:
            mainD['campaignLink'] = instance.getShortUrl()#f"{settings.FRONTEND_URL}/preview/{data['groupcampaign']}/?email={data['uniqueIdentity']}"
        return mainD


def codeForMailClient(mailClient,campaignId):
    emailAsClient = '{{email}}'
    thubmbnailUrl = f'{settings.BASE_URL}/campaign/thumbnail/?campaign={campaignId}&uid={emailAsClient}'
    campaignUrl = f"{settings.FRONTEND_URL}/preview/{campaignId}/?email={emailAsClient}"
    codeHtml = f'''
    <div style="width: 100%; max-width: 560px; text-align: center;">
        <div style="width: 100%; max-width: 560px;display: flex;
            background: #F6F6F6; border-top-left-radius: 5px; border-top-right-radius:
            5px; border: 1px solid rgba(117,117,117,0.1);">
                <span style="width: 100%;">
                    <a href="{campaignUrl}" target="_blank">
                        <img src="{thubmbnailUrl}"
                            style="max-width: 560px; text-align: center; display: table-cell; margin: auto;">
                    </a>
                    <span style="width: 100%; height: 100%"></span>
                </span>
        </div>
        <div style="width: 100; height: 25px; background: #FAFAFA; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; border: 1px solid
            rgba(117, 117, 117,0.1); border-top: none;">
    
            <div style="padding-left: 10px; padding-bottom: 5px; letter-spacing: 0.3px; font-family: Open Sans; font-size: 13px;">
                <a href="{campaignUrl}" target="_blank" style="color: #757575; text-decoration: none;">
                    Click to Preview
                </a>
            </div>
        </div>
    </div>'''
    return codeHtml


class GroupCampaignSerializer(serializers.ModelSerializer):
    csvFile = FileUploadSerializer()

    class Meta:
        model = GroupCampaign
        fields = ('id','campaign','mailClient','csvFile','timestamp','isAdded','isGenerated','totalData')

    def to_representation(self, instance):
        data = super(GroupCampaignSerializer, self).to_representation(instance)
        data['code']= codeForMailClient(data['mailClient'],data['id'])
        
        allQuery = GroupSingleCampaign.objects.filter(groupcampaign=data['id'])
        count = 0
        if allQuery:
            count = allQuery.filter(genVideo__status=1).count()
        if not data['isAdded']:
            data['completed'] = 0
        else:
            data['completed'] = count
        data.pop('isAdded')
        if not data['isGenerated']:
            if allQuery.exclude(genVideo__status=2).count()==data['totalData']:
                instance.isGenerated = True
                instance.save()
                data['isGenerated'] = True
        return data
