from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import json
from django.db.models import Q
from django.utils.timezone import now

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync




COMMAND = (
    (0,'SENT'),
    (2,'OPENED'),
    (3,'VIDEO PLAYED'),
    (4,'CTA CLICKED'),
    (5,'CROUSEL CLICKED')
)
GCOMMAND = (
    (0,'SENT'),
    (1,'MAIL OPENED'),
    (2,'OPENED'),
    (3,'VIDEO PLAYED'),
    (4,'CTA CLICKED'),
    (5,'CROUSEL CLICKED')
)


class CampaignGroupAnalytics(models.Model):

    campaign = models.ForeignKey('campaign.GroupSingleCampaign', on_delete=models.CASCADE)
    command = models.IntegerField(default= 0,choices=GCOMMAND)
    data = models.CharField(max_length=100,default='')
    cData = models.CharField(max_length=1000,default='')

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class CampaignSingleAnalytics(models.Model):

    campaign = models.ForeignKey('campaign.SoloCampaign', on_delete=models.CASCADE)
    command = models.IntegerField(default= 0,choices=COMMAND)
    data = models.CharField(max_length=100,default='')
    cData = models.CharField(max_length=1000,default='')

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    
    class Meta:
        ordering = ['-timestamp']



PSTATUS = (
    (0,'Pending'),
    (1,'Meeting Booked'),
    (2,'Snooze for 7 Days'),
    (3,'Snooze for 30 Days'),
    (4,'Sale Success'),
    (5,'Nothing Saled'),

)




CAMPTYPE = (
    (0,'SOLO'),
    (1,'GROUP')
)


class CampaignProspect(models.Model):

    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    uniqueIdentity = models.CharField(max_length=100)

    groupm = models.ForeignKey('campaign.GroupSingleCampaign', blank=True, null=True,on_delete=models.CASCADE)
    solom = models.ForeignKey('campaign.SoloCampaign', blank=True, null=True,on_delete=models.CASCADE)
    
    isSent = models.BooleanField(default=False)
    sentTime = models.DateTimeField(null=True, blank=True)

    isMailedOpend = models.BooleanField(default=False)
    mailOTime = models.DateTimeField(null=True, blank=True)

    isLinkedOpend = models.BooleanField(default=False)
    linkOTime = models.DateTimeField(null=True, blank=True)

    isVideoPlayed = models.BooleanField(default=False)
    videoPTime = models.DateTimeField(null=True, blank=True)
    videoData = models.CharField(max_length=1000,blank=True,null=True)

    isCollateral = models.BooleanField(default=False)
    collateralTime = models.DateTimeField(null=True, blank=True)
    collateralData = models.CharField(max_length=1000,blank=True,null=True)

    isCtaClicked = models.BooleanField(default=False) 
    ctaCTime = models.DateTimeField(null=True, blank=True)
    ctaData = models.CharField(max_length=1000,blank=True,null=True)


    prospectStatus = models.IntegerField(default= 0,choices=PSTATUS)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        unique_together = ('campaign', 'groupm','solom')
        constraints = [
            models.UniqueConstraint(fields=['campaign','groupm'], condition=Q(solom__isnull=True), name='unique__campaign_group__when__solo__null_prospect'),
            models.UniqueConstraint(fields=['campaign', 'solom'],condition=Q(groupm__isnull=True), name='unique__campaign_solo__when__group__null_prospect')
        ]
        ordering = ['-updated','-timestamp']



class CombinedAnalytics(models.Model):

    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    group = models.ForeignKey(CampaignGroupAnalytics, blank=True, null=True,on_delete=models.CASCADE)
    solo = models.ForeignKey(CampaignSingleAnalytics, blank=True, null=True,on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)

    isRead = models.BooleanField(default=False)
    signalDeleted = models.BooleanField(default=False)

    
    timestamp = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-timestamp']



class CampaignEmailOpenedAnalytics(models.Model):

    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)
    uniqueIdentity = models.CharField(max_length=100)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('campaign', 'uniqueIdentity')


class CampaignVideoPlayedAnalytics(models.Model):
    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)
    uniqueIdentity = models.CharField(max_length=100)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('campaign', 'cpros')


class CampaignOpenAnalytics(models.Model):
    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)
    uniqueIdentity = models.CharField(max_length=100)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('campaign', 'cpros')
        

class CampaignSentAnalytics(models.Model):
    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)
    uniqueIdentity = models.CharField(max_length=100)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('campaign', 'cpros')


class CampaignCtaClickedtAnalytics(models.Model):
    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)

    buttonId = models.IntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('campaign', 'cpros','buttonId')


class CampaignCollateralClickedtAnalytics(models.Model):
    campaign = models.ForeignKey('campaign.MainCampaign',on_delete=models.CASCADE)
    cpros = models.ForeignKey(CampaignProspect,on_delete=models.CASCADE)

    fileId = models.IntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('campaign', 'cpros','fileId')
    

from campaignAnalytics.serializers import (
    CombinedAnalyticsSignalSerializer,
    DashProspectSerializer
)
@receiver(post_save, sender=CampaignSingleAnalytics)
def addToMainSolo(sender, instance, created, **kwargs):

    myTInstQ = CampaignProspect.objects.filter(campaign=instance.campaign.campaign,uniqueIdentity = instance.campaign.uniqueIdentity)
    if myTInstQ.count()>=1:
        for myTInstI in myTInstQ:
            if myTInstI.solom:
                if myTInstI.solom.id != instance.campaign.id:
                    myTInstI.solom.delete()
            else:
                myTInstI.groupm.delete()

    pinst,ct = CampaignProspect.objects.get_or_create(campaign=instance.campaign.campaign,solom=instance.campaign,uniqueIdentity=instance.campaign.uniqueIdentity)
    t,created = CombinedAnalytics.objects.get_or_create(campaign=instance.campaign.campaign,solo=instance,cpros=pinst)
    t.timestamp=instance.timestamp
    t.save()
    if created:
        if instance.command!=0:
            signalData = {"type": "signal","data": CombinedAnalyticsSignalSerializer(t).data}#,{"type": "prospect","data": DashProspectSerializer(pinst).data}]
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(pinst.campaign.user.pk),
                {
                    "type": "sendSignals",
                    "text": signalData,
                },
            )

    if ct:
        salespageD = json.loads(instance.campaign.salesPageData)
        allBt = {}
        for i in salespageD['buttonEditor']:
            if i['isDeleted'] == False:
                for j in i['buttonData']:
                    if j['isDeleted'] == False:
                        allBt[j['id']] = {'name': j['name'],'isClicked': False}
        pinst.ctaData = json.dumps(allBt)

        allCt = {}
        for i in salespageD['crouselEditor']:
            if i['isDeleted'] == False:
                for j in i['crouselData']:
                    allCt[j['id']] = {'name': j['name'],'isClicked': False}

        pinst.collateralData = json.dumps(allCt)
        pinst.videoData = json.dumps({'name': pinst.campaign.video.name,'isClicked': False})
        pinst.save()
    
    if instance.command==0:
        pinst.isSent = True
        pinst.sentTime = instance.timestamp
        pinst.save()

        try:
            inst__ = CampaignSentAnalytics(campaign=instance.campaign.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
            inst__.save()
        except Exception as e:
            print('Mail Add : ',e)

    if instance.command>=1:

        if instance.command == 2:
            pinst.isLinkedOpend = True
            pinst.linkOTime = instance.timestamp
            pinst.save()

            try:
                inst__ = CampaignOpenAnalytics(campaign=pinst.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
        elif instance.command == 3:
            pinst.isVideoPlayed = True
            pinst.videoPTime = instance.timestamp
            ctm = json.loads(instance.cData)
            try:
                pinst.videoData = json.dumps({'name': ctm['name'],'isClicked': True})
            except:
                pinst.videoData = json.dumps({'name': pinst.campaign.video.name,'isClicked': True})

            pinst.save()
            try:
                inst__ = CampaignVideoPlayedAnalytics(campaign=pinst.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
        elif instance.command == 4:
            pinst.isCtaClicked = True
            pinst.ctaCTime = instance.timestamp
            ctm = json.loads(pinst.ctaData)
            ctc = json.loads(instance.cData)
            ctm[str(ctc['id'])]['isClicked'] = True

            try:
                inst__ = CampaignCtaClickedtAnalytics(campaign=pinst.campaign,cpros=pinst,buttonId=ctc['id'],timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
            pinst.ctaData = json.dumps(ctm)

            pinst.save()
        elif instance.command == 5:
            pinst.isCollateral = True
            pinst.collateralTime = instance.timestamp
            ctm = json.loads(pinst.collateralData)
            ctc = json.loads(instance.cData)
            ctm[str(ctc['id'])]['isClicked'] = True

            try:
                inst__ = CampaignCollateralClickedtAnalytics(campaign=pinst.campaign,cpros=pinst,fileId=ctc['id'],timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)

            pinst.collateralData = json.dumps(ctm)

            pinst.save()

        try:
            query = CampaignProspect.objects.filter(campaign__user=pinst.campaign.user)
            signalData = {"type": "prospect","data": DashProspectSerializer(pinst).data,"uniqueIdentity": pinst.uniqueIdentity,"campaign_name": pinst.campaign.name,"campaign_id": pinst.campaign.id,'totalCampaign': query.distinct('campaign__id').order_by().count(),'totalProspect': query.count()} #,{"type": "prospect","data": ]
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(pinst.campaign.user.pk),
                {
                    "type": "sendSignals",
                    "text": signalData,
                },
            )
        except:
            pass

        
        
    
    


@receiver(post_save, sender=CampaignGroupAnalytics)
def addToMainGroup(sender, instance, created, **kwargs):

    myTInstQ = CampaignProspect.objects.filter(campaign=instance.campaign.groupcampaign.campaign,uniqueIdentity = instance.campaign.uniqueIdentity)
    if myTInstQ.count()>=1:
        for myTInstI in myTInstQ:
            if myTInstI.groupm:
                if myTInstI.groupm.id != instance.campaign.id:
                    myTInstI.groupm.delete()
            else:    
                myTInstI.solom.delete()
    
    pinst,ct = CampaignProspect.objects.get_or_create(campaign=instance.campaign.groupcampaign.campaign,groupm=instance.campaign,uniqueIdentity = instance.campaign.uniqueIdentity)
    t,created = CombinedAnalytics.objects.get_or_create(campaign=instance.campaign.groupcampaign.campaign,group=instance,cpros=pinst)
    t.timestamp=instance.timestamp
    t.save()
    if created:
        if instance.command!=0:
            signalData = {"type": "signal","data": CombinedAnalyticsSignalSerializer(t).data}#,{"type": "prospect","data": DashProspectSerializer(pinst).data}]
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(pinst.campaign.user.pk),
                {
                    "type": "sendSignals",
                    "text": signalData,
                },
            )


    if ct:
        salespageD = json.loads(instance.campaign.salesPageData)
        allBt = {}
        for i in salespageD['buttonEditor']:
            if i['isDeleted'] == False:
                for j in i['buttonData']:
                    if j['isDeleted'] == False:
                        allBt[j['id']] = {'name': j['name'],'isClicked': False}

        pinst.ctaData = json.dumps(allBt)

        allCt = {}
        for i in salespageD['crouselEditor']:
            if i['isDeleted'] == False:
                for j in i['crouselData']:
                    allCt[j['id']] = {'name': j['name'],'isClicked': False}
                    
        pinst.collateralData = json.dumps(allCt)

        pinst.videoData = json.dumps({'name': pinst.campaign.video.name,'isClicked': False})
        pinst.save()

    if instance.command==0:
        pinst.isSent = True
        pinst.sentTime = instance.timestamp
        pinst.save()
        try:
            inst__ = CampaignSentAnalytics(campaign=instance.campaign.groupcampaign.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
            inst__.save()
        except Exception as e:
            print('Mail Add : ',e)

    if instance.command>=1:
        if instance.command == 1:
            pinst.isMailedOpend = True
            pinst.mailOTime = instance.timestamp

            pinst.save()
            try:
                inst__ = CampaignEmailOpenedAnalytics(campaign=pinst.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
        elif instance.command == 2:
            pinst.isLinkedOpend = True
            pinst.linkOTime = instance.timestamp
            pinst.save()

            try:
                inst__ = CampaignOpenAnalytics(campaign=pinst.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
        elif instance.command == 3:
            pinst.isVideoPlayed = True
            pinst.videoPTime = instance.timestamp
            ctm = json.loads(instance.cData)
            try:
                pinst.videoData = json.dumps({'name': ctm['name'],'isClicked': True})
            except:
                pinst.videoData = json.dumps({'name': pinst.campaign.video.name,'isClicked': True})
            pinst.save()
            try:
                inst__ = CampaignVideoPlayedAnalytics(campaign=pinst.campaign,cpros=pinst,uniqueIdentity=instance.campaign.uniqueIdentity,timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
        elif instance.command == 4:
            pinst.isCtaClicked = True
            pinst.ctaCTime = instance.timestamp
            ctm = json.loads(pinst.ctaData)
            ctc = json.loads(instance.cData)
            ctm[str(ctc['id'])]['isClicked'] = True
            try:
                inst__ = CampaignCtaClickedtAnalytics(campaign=pinst.campaign,cpros=pinst,buttonId=ctc['id'],timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)
            pinst.ctaData = json.dumps(ctm)
            pinst.save()
        elif instance.command == 5:
            pinst.isCollateral = True
            pinst.collateralTime = instance.timestamp
            ctm = json.loads(pinst.collateralData)
            ctc = json.loads(instance.cData)
            ctm[str(ctc['id'])]['isClicked'] = True

            try:
                inst__ = CampaignCollateralClickedtAnalytics(campaign=pinst.campaign,cpros=pinst,fileId=ctc['id'],timestamp=t.timestamp)
                inst__.save()
            except Exception as e:
                print('Mail Add : ',e)

            pinst.collateralData = json.dumps(ctm)
            pinst.save()

        try:
            query = CampaignProspect.objects.filter(campaign__user=pinst.campaign.user)
            signalData = {"type": "prospect","data": DashProspectSerializer(pinst).data,"uniqueIdentity": pinst.uniqueIdentity,"campaign_name": pinst.campaign.name,"campaign_id": pinst.campaign.id,'totalCampaign': query.distinct('campaign__id').order_by().count(),'totalProspect': query.count()} #,{"type": "prospect","data": ]
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(pinst.campaign.user.pk),
                {
                    "type": "sendSignals",
                    "text": signalData,
                },
            )
        except:
            pass

