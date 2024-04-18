from enum import unique
from django.db import models
from django.db.models import Q
from rest_framework import serializers

from campaign.models import (
    GroupSingleCampaign, MainCampaign,SoloCampaign,
    GroupCampaign
)
from campaignAnalytics.models import (
    CampaignSingleAnalytics,CampaignGroupAnalytics,
    CombinedAnalytics,CampaignProspect,CampaignCtaClickedtAnalytics,
    CampaignCollateralClickedtAnalytics
)
import json
from django.contrib.humanize.templatetags import humanize


class CombinedAnalyticsSignalSerializer(serializers.ModelSerializer):

    class Meta:
        model = CombinedAnalytics
        fields = ('id','isRead','timestamp')

    def to_representation(self, instance):
        data = super(CombinedAnalyticsSignalSerializer, self).to_representation(instance)
        if instance.group:
            inst = instance.group
        else:
            inst = instance.solo
        
        data['uniqueIdentity'] = inst.campaign.uniqueIdentity
        data['command'] = inst.command
        data['campaign_name'] = instance.campaign.name
        data['campaign_id'] = str(instance.campaign.id)

        data['data'] = ''
        if inst.command == 3:
            try:
                cdd = json.loads(inst.cData)
                data['data'] = cdd['name']
            except:
                pass
        
        if inst.command == 4:
            try:
                cdd = json.loads(inst.cData)
                data['data'] = cdd['name']
            except:
                pass
        elif inst.command == 5:
            try:
                cdd = json.loads(inst.cData)
                data['data'] = cdd['name']
            except:
                pass

        #data['hDateRemaining'] = humanize.naturaltime(instance.timestamp)

        # message = ''
        # if instance.group:
        #     inst = instance.group
        #     if inst.command==1:
        #         message = f"{inst.campaign.uniqueIdentity} opened mail."
        # else:
        #     inst = instance.solo
        
        # if inst.command == 2:
        #     message = f"{inst.campaign.uniqueIdentity} opened."
        # elif inst.command == 3:
        #     message = f"{inst.campaign.uniqueIdentity} played video."
        # elif inst.command == 4:
        #     try:
        #         cdd = json.loads(inst.cData)
        #         message = f"{inst.campaign.uniqueIdentity} clicked on {cdd['name']}."
        #     except:
        #         message = f"{inst.campaign.uniqueIdentity} clicked on ."
        # elif inst.command == 5:
        #     try:
        #         cdd = json.loads(inst.cData)
        #         message = f"{inst.campaign.uniqueIdentity} clicked on crousel {cdd['name']}."
        #     except:
        #         message = f"{inst.campaign.uniqueIdentity} clicked on on crousel ."
        # data['message'] = message
        # data['hDateRemaining'] = humanize.naturaltime(instance.timestamp)
        # data['messageType'] = inst.command
        return data

class CombinedAnalyticsSignalProspectSerializer(serializers.ModelSerializer):

    class Meta:
        model = CombinedAnalytics
        fields = ('id','isRead','timestamp')

    def to_representation(self, instance):
        data = super(CombinedAnalyticsSignalProspectSerializer, self).to_representation(instance)
        if instance.group:
            inst = instance.group
        else:
            inst = instance.solo
        data['command'] = inst.command

        data['data'] = ''
        if inst.command == 3:
            try:
                cdd = json.loads(inst.cData)
                data['data'] = cdd['name']
            except:
                pass
        elif inst.command == 4:
            try:
                cdd = json.loads(inst.cData)
                data['data'] = cdd['name']
            except:
                pass
        elif inst.command == 5:
            try:
                cdd = json.loads(inst.cData)
                data['data'] = cdd['name']
            except:
                pass
        return data


class CampaignProspectSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignProspect
        fields = '__all__'

    def to_representation(self, instance):
        data = super(CampaignProspectSerializer, self).to_representation(instance)

        if instance.groupm:
            inst = instance.groupm
            type_ = 'group'
        else:
            inst = instance.solom
            type_ = 'solo'
        data.pop('solom')
        data.pop('groupm')
        try:
            data['ctaData'] = list(json.loads(data['ctaData']).values())
        except:
            data['ctaData'] = []
        try:
            data['collateralData'] = list(json.loads(data['collateralData']).values())
        except:
            data['collateralData'] = []
        try:
            data['videoData'] = json.loads(data['videoData'])
        except:
            data['videoData'] = None
            if data['isVideoPlayed']:
                data['videoData'] = {'name': instance.campaign.video.name,'isClicked': True}
            else:
                data['videoData'] = {'name': instance.campaign.video.name,'isClicked': False}

        data['uniqueIdentity'] = inst.uniqueIdentity
        data['campaign_name'] = instance.campaign.name
        signalQuery = CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,cpros=instance,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,cpros=instance,signalDeleted=False)
        data['signals'] = CombinedAnalyticsSignalProspectSerializer(signalQuery,many=True).data
        data['type'] = type_
        return data



class CampaignSoloBriefSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignProspect
        fields = ('id','uniqueIdentity','isLinkedOpend','isVideoPlayed','isCollateral','isCtaClicked')

    def to_representation(self, instance):
        data = super(CampaignSoloBriefSerializer, self).to_representation(instance)
        data['campaign_id']=instance.campaign.id
        data['campaign_name']=instance.campaign.name

        return data



class CampaignGroupDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignProspect
        fields = ('id','uniqueIdentity','isLinkedOpend','isVideoPlayed','isCollateral','isCtaClicked')

    def to_representation(self, instance):
        data = super(CampaignGroupDetailsSerializer, self).to_representation(instance)
        #data['campaign_id']=instance.campaign.id
        #data['campaign_name']=instance.campaign.name

        return data


class CampaignGroupBriefSerializer(serializers.ModelSerializer):

    class Meta:
        model = GroupCampaign
        fields = ('id',)

    def to_representation(self, instance):
        data = super(CampaignGroupBriefSerializer, self).to_representation(instance)
        data = {'name': instance.csvFile.name,'total': instance.totalData,'LinkedOpend': 0,'VideoPlayed': 0,'Collateral': 0,'CtaClicked': 0,'campaign_id': instance.campaign.id,'campaign_name': instance.campaign.name,'groupCampId': data['id']}

        allAnalyt=CampaignProspect.objects.filter(groupm__groupcampaign=instance)
        
        data['LinkedOpend'] = allAnalyt.filter(isLinkedOpend=True).count()
        data['MailedOpend'] = allAnalyt.filter(isMailedOpend=True).count()
        data['VideoPlayed'] = allAnalyt.filter(isVideoPlayed=True).count()


        tempC = allAnalyt.filter(isCollateral=True)
        data['Collateral'] = CampaignCollateralClickedtAnalytics.objects.filter(cpros__in=tempC.values_list('id',flat=True)).count()
        tempC = allAnalyt.filter(isCtaClicked=True)
        data['CtaClicked'] = CampaignCtaClickedtAnalytics.objects.filter(cpros__in=tempC.values_list('id',flat=True)).count()

        return data


class CampaignAllBriefSerializer(serializers.ModelSerializer):

    class Meta:
        model = MainCampaign
        fields = ('id',)

    def to_representation(self, instance):
        data = super(CampaignAllBriefSerializer, self).to_representation(instance)
        data = {'LinkedOpend': 0,'MailOpened': 0,'VideoPlayed': 0,'Collateral': 0,'CtaClicked': 0,'campaign_id': instance.id,'campaign_name': instance.name}

        allAnalyt=CampaignProspect.objects.filter(campaign=instance)
        
        data['LinkedOpend'] = allAnalyt.filter(groupm__isnull=True,isLinkedOpend=True).count()
        #data['MailSent'] = allAnalyt.filter(solom__isnull=True,isSent=True).count()
        data['MailOpened'] = allAnalyt.filter(isMailedOpend=True).count()
        data['VideoPlayed'] = allAnalyt.filter(isVideoPlayed=True).count()

        tempC = allAnalyt.filter(isCollateral=True)
        data['Collateral'] = CampaignCollateralClickedtAnalytics.objects.filter(cpros__in=tempC.values_list('id',flat=True)).count()
        tempC = allAnalyt.filter(isCtaClicked=True)
        data['CtaClicked'] = CampaignCtaClickedtAnalytics.objects.filter(cpros__in=tempC.values_list('id',flat=True)).count()


        return data


class DashProspectSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignProspect
        fields = ('isSent','sentTime','isMailedOpend','mailOTime','isLinkedOpend','linkOTime','isVideoPlayed','videoPTime','videoData','isCollateral','collateralTime','collateralData','isCtaClicked','ctaCTime','ctaData')

    def to_representation(self, instance):
        data = super(DashProspectSerializer, self).to_representation(instance)

        if instance.groupm:
            type_ = 'group'
        else:
            type_ = 'solo'

        try:
            data['ctaData'] = list(json.loads(data['ctaData']).values())
        except:
            data['ctaData'] = []
        try:
            data['collateralData'] = list(json.loads(data['collateralData']).values())
        except:
            data['collateralData'] = []

        try:
            data['videoData'] = json.loads(data['videoData'])
        except:
            data['videoData'] = None
            if data['isVideoPlayed']:
                data['videoData'] = {'name': instance.campaign.video.name,'isClicked': True}
            else:
                data['videoData'] = {'name': instance.campaign.video.name,'isClicked': False}

        data['campaign_name'] = instance.campaign.name
        signalQuery = CombinedAnalytics.objects.filter(~Q(solo__command=0),group__isnull=True,cpros=instance,signalDeleted=False) | CombinedAnalytics.objects.filter(~Q(group__command=0),solo__isnull=True,cpros=instance,signalDeleted=False)
        data['signals'] = CombinedAnalyticsSignalProspectSerializer(signalQuery,many=True).data
        data['type'] = type_
        return data




class DashboardProspectSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignProspect
        fields = ('uniqueIdentity',)

    def to_representation(self, instance):
        data = super(DashboardProspectSerializer, self).to_representation(instance)

        allUserData = CampaignProspect.objects.filter(campaign__user=instance.campaign.user,uniqueIdentity=data['uniqueIdentity']).order_by('-updated')
        
        
        data['campData'] = DashProspectSerializer(allUserData,many=True).data
        data['prospectStatus'] = allUserData.first().prospectStatus
        return data
