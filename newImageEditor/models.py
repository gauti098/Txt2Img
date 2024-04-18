from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _


from django.utils import timezone
from shutil import copy
from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob
from appAssets import models as appAssetsModels

from uuid import uuid4,UUID
import traceback,os
import uuid
import requests,json
from newVideoCreator import task as newVideoCreatorTask
import logging
from django.utils.crypto import get_random_string
import string


from utils.common import getParsedText
logger = logging.getLogger(__name__)


CANVAS_RATIO = (
    (0,"16:9"),
    (1,"1:1"),
    (2,"9:16"),
)

TEMPLATE_CATEGORY = (
    (0,"NO"),
    (1,"Verified"),
    (2,"Not Verified"),
)
IMAGE_GENERATED_TYPE = (
    (0,'REAL_TIME'),
    (1,'SOLO_LINK'),
)

IMAGECREATORGENERATED_UUID_TOTAL_NO = 3
class ImageCreatorGenerated(models.Model):
    # Custom fields
    _uid = models.UUIDField(default = uuid.uuid4, unique=True,editable = False)
    imageCreator = models.ForeignKey('ImageCreator', on_delete=models.CASCADE)
    mergeTagValue = models.TextField(blank=True,null=True)
    isGenerated = models.BooleanField(default=False)
    generationType = models.IntegerField(default= 0,choices=IMAGE_GENERATED_TYPE)
    thumbnail = models.ImageField(upload_to='newvideocreator/imagecreator/generated/')
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/imagecreator/generated/")
        os.makedirs(_path,exist_ok=True)
        return _path

    def getThumbnailName(self):
        filename = f"{self._uid}.jpeg"
        return f"newvideocreator/imagecreator/generated/{filename}"

    def getThumbnailPath(self):
        _path = self.getCwd()
        filename = f"{self._uid}.jpeg"
        return os.path.join(_path,filename)

    def generateImage(self,_tagKeys=None,_tagValues=None,creditType="PERSONALIZE_IMAGE"):
        if _tagValues==None:
            _tagValues = json.loads(self.mergeTagValue)
        if _tagKeys==None:
            _tagKeys = json.loads(self.imageCreator.mergeTag)
        self.thumbnail.name = self.getThumbnailName()
        self.save()

        _thumbnailPath = self.getThumbnailPath()
        _renderData = {"id": self.imageCreator.id,"isImage": True,"data": [{"scene": 0,"outputPath": _thumbnailPath}]}
        if len(_tagValues):
            _renderData['isPersonalized'] = True
            _renderData['mergeData'] = {'key': _tagKeys,'value': _tagValues}

        _url = settings.REAL_TIME_THUMBNAIL_GENERATE_BASE_URL + "/generate/"
        _r = requests.post(_url,data=json.dumps(_renderData),headers={'Content-Type': 'application/json'})
        try:
            _resD = _r.json()
            if not _resD["isError"]:
                self.thumbnail.name = self.getThumbnailName()
                self.isGenerated = True
                self.save()
                _meta = {"type": creditType,"usedCredit": 1,"id": f"{self.id}","imageId": f"{self.imageCreator.id}","name": f"{self.imageCreator.name}","userId": f"{self.imageCreator.user.id}"}
                newVideoCreatorTask.addCreditTask.delay(_meta)

        except:
            pass
        return (_thumbnailPath,self.thumbnail.url)


     


@receiver(models.signals.post_delete, sender=ImageCreatorGenerated)
def auto_delete_thumbnail(sender, instance, **kwargs):
    if instance.thumbnail:
        if os.path.isfile(instance.thumbnail.path):
            os.remove(instance.thumbnail.path)


class ImageCreator(models.Model):
    # Custom fields
    _uid = models.UUIDField(default = uuid.uuid4,unique=True,editable = False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=250,blank=True,null=True,default='Untitled Image')
    jsonData = models.TextField(blank=True,null=True)
    mergeTag = models.CharField(default="[]",max_length=5000,blank=True,null=True)
    isPersonalized = models.BooleanField(default=False)
    isGenerated = models.BooleanField(default=False)
    isDeleted = models.BooleanField(default=False)

    thumbnail = models.ImageField(upload_to='newvideocreator/imagecreator/thumbnail/',default='newvideocreator/imagecreator/thumbnail/default.jpg')
    mailClient = models.ForeignKey("campaign.EmailClient", on_delete=models.SET_DEFAULT,default=1)
    redirectUrl = models.CharField(max_length=500,blank=True,null=True)

    ratio = models.IntegerField(default= 0,choices=CANVAS_RATIO)
    _videoId = models.IntegerField(blank=True,null=True)
    isAutoGenerated = models.BooleanField(default=False)
    isTemplate = models.IntegerField(default=0,choices=TEMPLATE_CATEGORY)

    # used video as campaign
    slug = models.CharField(max_length=64,blank=True,null=True)

    generatedAt = models.DateTimeField(default=timezone.now)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} {self.id}"

    def setUniqueSlug(self,isShort=True):
        RETRY = 180
        
        if isShort:
            complexity = 4
        else:
            complexity = 32

        for ii in range(RETRY):
            _complexity = complexity + int(ii/5)
            _slug = get_random_string(_complexity,allowed_chars=string.ascii_lowercase+string.digits)

            query = ImageCreator.objects.filter(slug=_slug)
            if not query:
                self.slug = _slug
                self.save()
                return _slug


    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/imagecreator/thumbnail/")
        os.makedirs(_path,exist_ok=True)
        return _path

    def getThumbnailName(self,filename):
        return f"newvideocreator/imagecreator/thumbnail/{filename}"

    def getThumbnailPath(self,filename):
        _path = self.getCwd()
        return os.path.join(_path,filename)
    

    def onGenerate(self):
        self.isGenerated = True
        _mergeTag = self.getMergeTag()
        self.generatedAt = timezone.now()
        if _mergeTag:
            self.isPersonalized = True
            self.mergeTag = json.dumps(_mergeTag)
        self.save()
        if not self.isAutoGenerated:
            self.updateThumbnail()
    
    def getData(self):
        return json.loads(self.jsonData)

    def getSceneArray(self,currentScene):
        _sceneArr = currentScene.get('arr',None)
        if _sceneArr!=None:
            allScene = json.loads(_sceneArr)
            return [str(i) for i in allScene if i!=-1]
        else:
            _sceneArr = currentScene.get('sceneArr',None)
            if _sceneArr!=None:
                allScene = json.loads(_sceneArr)
                return [str(i) for i in allScene if i!=-1]
            else:
                return []

    def replaceAvatar(self,avatarId=None):
        jsonData = self.getData()
        if not avatarId:
            return jsonData
        try:
            _avatarInst = appAssetsModels.AvatarImages.objects.get(id=avatarId)
            _newAvatarImageUrl = _avatarInst.transparentImage.url
            # replace avatar
            allSceneIndex = self.getSceneArray(jsonData["currentScene"])
            for _sceneIndex in allSceneIndex:
                _sceneData = jsonData[_sceneIndex]["jsonData"]["objects"]
                for d in _sceneData:
                    if d.get("_Type",None) == 'avatar':
                        _type = d.get("type",None)
                        if _type == "image":
                            d["src"] = _newAvatarImageUrl
                        elif _type == "group":
                            _gobj = d.get("objects",[])
                            if len(_gobj)==2:
                                _gobj[1]["src"] = _newAvatarImageUrl

            return jsonData
        except:
            return jsonData
        

        
    def getMergeTag(self):
        jsonData = self.getData()
        allSceneIndex = self.getSceneArray(jsonData["currentScene"])
        allMergeTag = []
        allAdded = {}
        for _sceneIndex in allSceneIndex:
            _sceneData = jsonData[_sceneIndex]["jsonData"]["objects"]
            try:
                _allTextBoxMTag = []
                for d in _sceneData:
                    if d['_Type'] == 'text':
                        _allTextBoxMTag.extend(getParsedText(d.get("text",""),onlyTag=True))
                
                for _tag in _allTextBoxMTag:
                    if not allAdded.get(f"{_tag}_text",None):
                        allAdded[f"{_tag}_text"] = True
                        allMergeTag.append([_tag,'text'])
            except:
                pass

            try:
                _allImgVar = list(set([ d.get('_Variable',"") for d in _sceneData if (d.get("type","") == 'image' and d.get('_Variable',"") and d.get('_haveMerge',False))]))
                _finalImageMTag = []
                for _var in _allImgVar:
                    if _var[:2] != "{{" and _var[-2:]!="}}":
                        _finalImageMTag.append("{{"+_var+"}}")
                    else:
                        _finalImageMTag.append(_var)

                for _tag in _finalImageMTag:
                    if not allAdded.get(f"{_tag}_url",None):
                        allAdded[f"{_tag}_url"] = True
                        allMergeTag.append([_tag,'url'])
            except:
                pass
        return allMergeTag

    def updateThumbnailWithMTag(self,mergeTagValue):
        if self.isPersonalized:
            _thumbnailPath = self.thumbnail.path
            if len(_thumbnailPath.split('default'))<=1:
                self.updateThumbnail()
            _mtag = json.loads(self.mergeTag)
            _renderData = {"id": self.id,"isImage": True,"data": [{"scene": 0,"outputPath": self.thumbnail.path}]}
            if len(_mtag):
                _renderData['isPersonalized'] = True
                _renderData['mergeData'] = {'key': _mtag,'value': mergeTagValue}
                rabbitMQSendJob('setDraftThumbnail',json.dumps(_renderData),durable=True)
        return 1

    def updateThumbnail(self,scene=0):
        outputPath = self.thumbnail.path
        uuidName = os.path.basename(outputPath)
        try:
            isValidUUid = UUID(uuidName.split('.')[0])
            isFound = os.path.isfile(outputPath)
            if not isFound:
                copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)
            # for updating thumbnail
            self.save()
        except:
            _filename = f"{uuid4()}.jpeg"
            outputPath = os.path.join(self.getCwd(),_filename)
            copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)
            self.thumbnail.name  = self.getThumbnailName(_filename)
            self.save()
        rabbitMQSendJob('setDraftThumbnail',json.dumps({"id": self.id,"isImage": True,"data": [{"scene": scene,"outputPath": outputPath}]}),durable=True)

    def update_jsonData(self,newData):
        _url = settings.NODE_SERVER_BASE_URL + f"/newvideocreate/{self.id}/"
        _data = json.dumps({"jsonData": newData,"isImage": True})
        _r = requests.put(_url,data=_data,headers={'Content-Type': 'application/json'})
        _resData = None
        try:
            _resData = _r.json()
        except:
            _resData = _r.content
        return (_r.status_code,_resData)

    def generateImageWithMTagRealtime(self,mtagValue={},creditType="PERSONALIZE_IMAGE",generationType=0):
        if not (self.isGenerated or self.isPersonalized):
            return (self.thumbnail.path,self.thumbnail.url,None)

        _mergeTags = json.loads(self.mergeTag)
        _mergeTagValue = []
        for _tag in _mergeTags:
            _mvalue = mtagValue.get(f"{_tag[0]}_{_tag[1]}",None)
            _mergeTagValue.append(_mvalue)
        _gInst,ct = ImageCreatorGenerated.objects.get_or_create(imageCreator=self,mergeTagValue=json.dumps(_mergeTagValue),generationType=generationType)
        if _gInst.isGenerated and _gInst.thumbnail:
            thumbnailPath = _gInst.thumbnail.path
            isFound = os.path.isfile(thumbnailPath)
            if not isFound:
                _tdata = _gInst.generateImage(_mergeTags,_mergeTagValue,creditType)
                return (_tdata[0],_tdata[1],_gInst)
            return (thumbnailPath,_gInst.thumbnail.url,_gInst)
        else:
            _tdata = _gInst.generateImage(_mergeTags,_mergeTagValue,creditType)
            return (_tdata[0],_tdata[1],_gInst)


@receiver(models.signals.post_delete, sender=ImageCreator)
def auto_delete_file_ImageCreator(sender, instance, **kwargs):
    if instance.thumbnail:
        if os.path.isfile(instance.thumbnail.path) and not instance.isAutoGenerated:
            if len(instance.thumbnail.path.split('default'))==1:
                os.remove(instance.thumbnail.path)