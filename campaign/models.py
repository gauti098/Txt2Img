from django.db import models
from django.contrib.auth import get_user_model

from django.conf import settings
# from aiQueueManager.models import (
#     VideoRenderMultipleScene,GeneratedFinalVideo
# )
from userlibrary.models import FileUpload
from salesPage.models import SalesPageEditor
import uuid,json,os,re
from urlShortner.models import CampaignUrlShortner

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from uuid import UUID,uuid1
import shutil


class SoloCampaign(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uniqueIdentity = models.CharField(max_length=100)
    campaign = models.ForeignKey('MainCampaign', on_delete=models.CASCADE)
    data = models.CharField(max_length=5000)
    genVideo = models.ForeignKey('aiQueueManager.GeneratedFinalVideo',on_delete=models.SET_NULL,null=True,blank=True)
    thumbnail = models.ImageField(upload_to='campagin/thumbnail/group/',default='videom/preview/default.jpg')
    salesPageData = models.CharField(max_length=50000)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"Solo Campaign {self.campaign.name}"
    
    class Meta:
        ordering = ['-timestamp']

    def getShortUrl(self):
        try:
            inst = CampaignUrlShortner.objects.get(_type=0,mainId=f"{self.id}",_appType=0)
        except:
            inst = CampaignUrlShortner(_type=0,mainId=f"{self.id}",_appType=0)
            _getSlug = inst.generateSlug()
            inst.slug = _getSlug
            inst.save()
        return inst.getUrl()





MAIL_CLIENT_CHOICES = (
    (0,'SendGrid'),
    (1,'Elastic Email'),
    (2,'Hubspot'),
    (3,'Mailgun'),
    (4,'SparkPost'),
    (5,'Salesforce'),
    (6,'MailChimp'),
    (7,'ActiveCampaign'),
    (8,'WoodPecker')
)


class EmailClient(models.Model):
    # Custom fields
    name = models.CharField(max_length=100)
    src = models.FileField(upload_to="campaign/emailclient/",default="campaign/emailclient/default.svg",blank=True)
    _data = models.CharField(max_length=5000,blank=True,null=True)
    _order = models.IntegerField(default=0)

    class Meta:
        ordering = ['-_order','name']

    def __str__(self):
        return self.name
    
    def getCode(self,campaignId,uid=False,PAGE_URL='https://autovid.ai/p',newLink=False):
        thubmbnailUrl = None
        campaignUrl = None
        if uid:
            if newLink:
                campaignUrl = f"{PAGE_URL}/{campaignId}/{uid}"
            else:
                campaignUrl = f"{PAGE_URL}/{campaignId}/?email={uid}"
            thubmbnailUrl = f'{settings.BASE_URL}/campaign/thumbnail/?isPlayBtn=1&campaign={campaignId}&uid={uid}'
        else:
            emailAsClient = '{{email}}'
            try:
                _d = json.loads(self._data)
                emailAsClient = _d.get("email",emailAsClient)
            except:
                pass
            thubmbnailUrl = f'{settings.BASE_URL}/campaign/thumbnail/?isPlayBtn=1&campaign={campaignId}&uid={emailAsClient}'
            if newLink:
                campaignUrl = f"{PAGE_URL}/{campaignId}/{emailAsClient}"
            else:
                campaignUrl = f"{PAGE_URL}/{campaignId}/?email={emailAsClient}__batch__"
        codeHtml = f'''<div style="width: 100%; max-width: 560px; text-align: center;"><div style="width: 100%; max-width: 560px;display: flex;background: #F6F6F6; border-top-left-radius: 5px; border-top-right-radius:5px; border: 1px solid rgba(117,117,117,0.1);"><span style="width: 100%;"><a href="{campaignUrl}" target="_blank"><img src="{thubmbnailUrl}"style="max-width: 560px; text-align: center; display: table-cell; margin: auto;"></a><span style="width: 100%; height: 100%"></span></span></div><div style="width: 100; height: 25px; background: #FAFAFA; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; border: 1px solidrgba(117, 117, 117,0.1); border-top: none;"><div style="padding-left: 10px; padding-bottom: 5px; letter-spacing: 0.3px; font-family: Open Sans; font-size: 13px;"><a href="{campaignUrl}" target="_blank" style="color: #757575; text-decoration: none;">Click to Preview</a></div></div></div>'''
        return codeHtml

    def getImageCode(self,thubmbnailUrl,campaignUrl='#',splited=False):
        if splited:
            codeHtml = [f'''<div style="width: 100%; max-width: 560px; text-align: center;"><div style="width: 100%; max-width: 560px;display: flex;background: #F6F6F6; border-top-left-radius: 5px; border-top-right-radius:5px; border: 1px solid rgba(117,117,117,0.1);"><span style="width: 100%;"><a href="''', f'''" target="_blank"><img src="{thubmbnailUrl}"style="max-width: 560px; text-align: center; display: table-cell; margin: auto;"></a><span style="width: 100%; height: 100%"></span></span></div><div style="width: 100; height: 25px; background: #FAFAFA; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; border: 1px solidrgba(117, 117, 117,0.1); border-top: none;"><div style="padding-left: 10px; padding-bottom: 5px; letter-spacing: 0.3px; font-family: Open Sans; font-size: 13px;"><a href="''',f'''" target="_blank" style="color: #757575; text-decoration: none;">Click to Preview</a></div></div></div>''']
            return codeHtml

        codeHtml = f'''<div style="width: 100%; max-width: 560px; text-align: center;"><div style="width: 100%; max-width: 560px;display: flex;background: #F6F6F6; border-top-left-radius: 5px; border-top-right-radius:5px; border: 1px solid rgba(117,117,117,0.1);"><span style="width: 100%;"><a href="{campaignUrl}" target="_blank"><img src="{thubmbnailUrl}"style="max-width: 560px; text-align: center; display: table-cell; margin: auto;"></a><span style="width: 100%; height: 100%"></span></span></div><div style="width: 100; height: 25px; background: #FAFAFA; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; border: 1px solidrgba(117, 117, 117,0.1); border-top: none;"><div style="padding-left: 10px; padding-bottom: 5px; letter-spacing: 0.3px; font-family: Open Sans; font-size: 13px;"><a href="{campaignUrl}" target="_blank" style="color: #757575; text-decoration: none;">Click to Preview</a></div></div></div>'''
        return codeHtml


class GroupCampaign(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('MainCampaign', on_delete=models.CASCADE)
    mailClient = models.IntegerField(default= 0,choices=MAIL_CLIENT_CHOICES)
    mergeTagMap = models.CharField(max_length=1000)
    csvFile = models.ForeignKey(FileUpload, on_delete=models.CASCADE)
    isAdded = models.BooleanField(default=False)
    isValidated = models.BooleanField(default=False)
    isGenerated = models.BooleanField(default=False)
    totalData = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"{self.campaign.name} => {self.id}"

    class Meta:
        ordering = ['-timestamp']


    def getCsvPath(self):
        tpath = f"private_data/validatedCSV/"
        os.makedirs(tpath,exist_ok=True)
        return os.path.join(tpath,f"{self.id}.csv")


from django.core.validators import validate_email
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import datetime


class GroupSingleCampaign(models.Model):

    uniqueIdentity = models.CharField(max_length=100)
    groupcampaign = models.ForeignKey('GroupCampaign', on_delete=models.CASCADE)
    data = models.CharField(max_length=5000)
    genVideo = models.ForeignKey('aiQueueManager.GeneratedFinalVideo',on_delete=models.SET_NULL,null=True,blank=True)

    thumbnail = models.ImageField(upload_to='campagin/thumbnail/group/',default='videom/preview/default.jpg')
    salesPageData = models.CharField(max_length=50000)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ('uniqueIdentity', 'groupcampaign',)

    def __str__(self):
        return f"Group Single Campaign {self.groupcampaign.campaign.name}"

    def getShortUrl(self):
        try:
            inst = CampaignUrlShortner.objects.get(_type=1,mainId=f"{self.id}",_appType=0,uniqeId=f"{self.uniqueIdentity}")
        except:
            inst = CampaignUrlShortner(_type=1,mainId=f"{self.id}",_appType=0,uniqeId=f"{self.uniqueIdentity}")
            _getSlug = inst.generateSlug()
            inst.slug = _getSlug
            inst.save()
        return inst.getUrl()

    def getOverAllGroup(self):
        groupCampaign = self.groupcampaign
        data = {"id": str(groupCampaign.id),"totalData": groupCampaign.totalData,"campaign": str(groupCampaign.campaign.id),"isGenerated": groupCampaign.isGenerated,"isDefault": self.genVideo.isDefault}
        allQuery = GroupSingleCampaign.objects.filter(groupcampaign=data['id'])
        count = allQuery.filter(genVideo__status=1).count()
        if not groupCampaign.isAdded:
            data['completed'] = 0
        else:
            data['completed'] = count

        if not groupCampaign.isGenerated:
            if allQuery.filter(genVideo__status=2).count()==0:
                groupCampaign.isGenerated = True
                groupCampaign.save()
                data['isGenerated'] = True
        signalData = {"type": "mainVideoProgressUpdate","data": data}
        return signalData

        
    def sendGroupCampaignEmail(self):
        from campaignAnalytics.models import CampaignGroupAnalytics
        try:
            groupInst = self.groupcampaign

            inst_ = CampaignGroupAnalytics(campaign=self,command=0)
            inst_.save()

            inst = groupInst.campaign
            validate_email(self.uniqueIdentity)
            template_prefix = 'campaign/campaign_group_email'
            open('/home/govind/sendgroupEmail.txt','a').write(f"{datetime.now()} ==> {self.uniqueIdentity} Sending\n")

            subject_file = '%s_subject.txt' % template_prefix
            txt_file = '%s.txt' % template_prefix
            html_file = '%s.html' % template_prefix

            template_ctxt = {
                'campaign_name': inst.name,
                'sender_email': inst.user.email,
                'name': self.uniqueIdentity.split('@')[0],
                'thumbnail_url': settings.BASE_URL + f"/campaign/thumbnail/?campaign={groupInst.id}&uid={self.uniqueIdentity}",
                'campaign_url': settings.FRONTEND_URL + '/preview/' + str(groupInst.id)+f'/?email={self.uniqueIdentity}'
            }
            
            from_email = settings.EMAIL_FROM
            bcc_email = settings.EMAIL_BCC

            subject = render_to_string(subject_file,template_ctxt).strip()
            text_content = render_to_string(txt_file, template_ctxt)
            html_content = render_to_string(html_file, template_ctxt)
            msg = EmailMultiAlternatives(subject, text_content, from_email, [self.uniqueIdentity],
                                        bcc=[bcc_email])
            msg.attach_alternative(html_content, 'text/html')
            if self.uniqueIdentity.lower() not in ['kiran@ut-ec.co.jp','kobayashi@ut-ec.co.jp']:
                if self.uniqueIdentity.lower().split('@')[-1] == 'gmail.com':
                    #msg.send()
                    pass
            open('/home/govind/sendgroupEmail.txt','a').write(f"{datetime.now()} ==> {self.uniqueIdentity} Send\n")
            return True
        except Exception as e:
            open('/home/govind/sendgroupEmail.txt','a').write(f"{datetime.now()} ==> {self.uniqueIdentity} Failed {e}\n")
            return False
        


class MainCampaign(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    video = models.ForeignKey('aiQueueManager.VideoRenderMultipleScene',on_delete=models.CASCADE)
    salespage = models.ForeignKey('salesPage.SalesPageEditor',on_delete=models.CASCADE)
    tags= models.CharField(max_length=1000,default="")
    thubmnailImage = models.ImageField(upload_to='campaign/preview/',default='campaign/preview/default.jpg')

    selectedThumbnail = models.ForeignKey('videoThumbnail.MainThumbnail',blank=True,null=True,on_delete=models.SET_NULL,related_name="MainCampaign_selectedThumbnail")


    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.name

    def setThumbnail(self):
        ## set thubmnail
        url = settings.FRONTEND_URL + f'/preview/{self.id}?email=campaign_test'
        outputPath = self.thubmnailImage.path
        uuidName = os.path.basename(outputPath)
        try:
            isValidUUid = UUID(uuidName.split('.')[0])
            isFound = os.path.isfile(outputPath)
            if isFound:
                _oldPath = outputPath
            outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
            if isFound:
                shutil.move(_oldPath,outputPath)
        except:
            outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
            shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)
        self.thubmnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
        self.save()
        data = {"type": "setSalesPageCampaignThumbnail","data": {"url": url,"outputPath": outputPath},"user": self.user.id,"returnType": "setCampaignThumbnail", "returnData": {"thubmnailImage": settings.BASE_URL + self.thubmnailImage.url,"id": str(self.id)}}
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "generateThumbnail",
            {
                "type": "setThumbnail",
                "text": data,
            },
        )
        return True


    def getUsedMergeTag(self,onlyVideo=True,onlySales=True):
        allMT = []
        if onlyVideo:
            allVideoTag = self.video.getUsedMergeTag(includeThumbnail=False,onlyList=True)
            allMT.extend(allVideoTag)
            
        ## salespage mergetag
        if onlySales:
            salesPageTag = self.salespage.getUsedMergeTag(onlyList=True)
            allMT.extend(salesPageTag)
        if onlySales and onlyVideo:
            if self.selectedThumbnail:
                allMT.extend(self.selectedThumbnail.getMergeTag())
        allMT = sorted(set(allMT))
        outputF = []
        for ind,ii in enumerate(allMT):
            outputF.append({"id": ind,"name": ii,"value": ii[2:-2]})
        return outputF

