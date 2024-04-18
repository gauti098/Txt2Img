from email.policy import default
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from userlibrary.models import FileUpload
from aiQueueManager.models import MergeTag
import re
from django.conf import settings

from utils.customValidators import validate_url

THUMBNAIL_TYPE= (
    (0,'UPLOAD'),
    (1,'VIDEO_FRAME'),
    (2,'CUSTOM_TEMPLATE'),
)




class SalesPageThumbnailCustomTemplate(models.Model):
    
    name = models.CharField(max_length=50)
    preview = models.IntegerField(default= 1,choices=THUMBNAIL_TYPE)



class SalesPageDetails(models.Model):
    
    salesPage = models.OneToOneField('SalesPageEditor', on_delete=models.CASCADE)
    pageLink = models.CharField(max_length=50,unique = True)
    favicon = models.ForeignKey(FileUpload,blank=True,null=True,on_delete=models.SET_NULL)

    def __str__(self):
        return f"SalesPageDetails: {self.salesPage.name}"
    
    class Meta:
        unique_together = ('salesPage', 'pageLink',)


class VideoCreatorTracking(models.Model):

    salespage = models.ForeignKey("SalesPageEditor", on_delete=models.CASCADE)
    videoCreator = models.ForeignKey("newVideoCreator.TempVideoCreator", on_delete=models.CASCADE)
    origin = models.CharField(blank=True,null=True,default="https://video.autogenerate.ai",max_length=100)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"{self.salespage.name} : {self.videoCreator.name}"


SALESPAGE_APP_TYPE = (
    (0,'SALESPAGE'),
    (1,'VIDEO_CREATOR'),
)
class SalesPageEditor(models.Model):
    
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    textEditor = models.ManyToManyField('TextEditor',blank=True)
    imageEditor = models.ManyToManyField('ImageEditor',blank=True)
    buttonEditor = models.ManyToManyField('ButtonDataEditor',blank=True)
    iconEditor = models.ManyToManyField('IconEditor',blank=True)
    videoEditor = models.ManyToManyField('VideoEditor',blank=True)
    crouselEditor = models.ManyToManyField('CrouselEditor',blank=True)

    themeColorConfig = models.CharField(max_length=5000,blank=True,null=True)

    isPublic = models.BooleanField(default=False)
    publicId = models.IntegerField(default=-1)

    isPublish = models.BooleanField(default=True)
    
    # for new video creator
    isPersonalized = models.BooleanField(default=False)
    mergeTag = models.CharField(blank=True,null=True,max_length=5000)
    appType = models.IntegerField(default=0,choices=SALESPAGE_APP_TYPE)
    isDefault = models.BooleanField(default=False)

    previewImage = models.ImageField(upload_to='salespage/preview/',default='salespage/preview/default.jpg')
    mobileViewPreview = models.ImageField(upload_to='salespage/public/mobile/',null=True,blank=True)
    desktopViewPreview = models.ImageField(upload_to='salespage/public/desktop/',null=True,blank=True)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"SalesPage: {self.name}"

    def setMergeTag(self):
        _allMTag = self.getUsedMergeTag(onlyList=True)
        if _allMTag:
            self.isPersonalized = True
            self.mergeTag = json.dumps(_allMTag)
            self.save()
        else:
            self.isPersonalized = False
            self.save()


    def getUsedMergeTag(self,onlyList=False):
        allMT = []
        for inst in self.textEditor.all():
            if not inst.isDeleted:
                allTag = ['{{'+ i+ '}}' for i in re.findall(settings.MERGE_TAG_PATTERN, inst.content) if len(i)<100]
                allMT.extend(allTag)
        
        allMT = sorted(set(allMT))
        if onlyList:
            return allMT
        else:
            outputF = []
            for ind,ii in enumerate(allMT):
                outputF.append({"id": ind,"name": ii,"value": ii[2:-2]})
            return outputF




@receiver(models.signals.pre_delete, sender=SalesPageEditor)
def delete_many_inst(sender, instance, *args, **kwargs):
    for inst in instance.textEditor.all():
        inst.delete()
    for inst in instance.imageEditor.all():
        inst.delete()
    for inst in instance.iconEditor.all():
        inst.delete()
    for inst in instance.videoEditor.all():
        inst.delete()

    for inst in instance.buttonEditor.all():
        inst.delete()
    for inst in instance.crouselEditor.all():
        inst.delete()
    

class TextEditor(models.Model):
    
    content = models.TextField(max_length=50000)
    isDeleted = models.BooleanField(default=False)

    def getId(self):
        return f"text{self.id}"

    class Meta:
        ordering = ['pk']



class ImageEditor(models.Model):

    image = models.URLField(blank=True,validators =[validate_url,])
    height = models.IntegerField(default=50)
    imgUrl = models.URLField(blank=True,validators =[validate_url,])
    isDeleted = models.BooleanField(default=False)

    def getId(self):
        return f"image{self.id}"

    class Meta:
        ordering = ['pk']

class IconEditor(models.Model):

    image = models.URLField(blank=False,validators =[validate_url,])
    link = models.URLField(blank=True,validators =[validate_url,])
    #iconClass = models.CharField(max_length=50,blank=True)
    isDeleted = models.BooleanField(default=False)

    def getId(self):
        return f"icon{self.id}"

    class Meta:
        ordering = ['pk']

class VideoEditor(models.Model):

    height = models.IntegerField(default=50)
    imgUrl = models.URLField(blank=True,validators =[validate_url,])
    isDeleted = models.BooleanField(default=False)

    def getId(self):
        return f"video{self.id}"
    
    class Meta:
        ordering = ['pk']
    
class ButtonDataEditor(models.Model):

    buttonData = models.ManyToManyField('ButtonEditor',blank=True)
    isDeleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['pk']

@receiver(models.signals.pre_delete, sender=ButtonDataEditor)
def delete_button_inst(sender, instance, *args, **kwargs):
    for inst in instance.buttonData.all():
        inst.delete()
    
class ButtonEditor(models.Model):

    name = models.CharField(max_length=100)
    link = models.URLField(blank=True,validators =[validate_url,])
    textColor = models.CharField(max_length=10)
    buttonColor = models.CharField(max_length=10)
    isDeleted = models.BooleanField(default=False)

    updated = models.DateTimeField(auto_now=True)

    def getId(self):
        return f"button{self.id}"
   
    class Meta:
        ordering = ['updated']

import json
class CrouselEditor(models.Model):

    crouselData = models.ManyToManyField(FileUpload,blank=True)
    orderId = models.CharField(max_length=1000,blank=True)
    isDeleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['pk']

    def save_order(self,id_list):
        self.orderId = json.dumps(id_list)
        self.save()
    
    def get_order(self):
        return json.loads(self.orderId)
   