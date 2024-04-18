from pyexpat import model
from typing import final
from django.db import models
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
import requests,json,os
from base64 import b64decode
from django.conf import settings
from uuid import uuid4,UUID
from django.db.models import Q

from datetime import datetime,timedelta
from django.utils import timezone

from shutil import copy,move
from aiAudio.models import AiAudio, AiCombineAudio
from aiAudio.views import aiGenerateSound
from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob
from events import fire

from appAssets.models import (
    AvatarImages,AvatarSounds
)
from newVideoCreator import task as newVideoCreatorTask


from newVideoCreator.utils.combineSceneVideoAudio import combineAudioVideo,combineVideoAtFileLevel
from salesPage.models import SalesPageEditor
from userlibrary.models import FileUpload
from utils.common import convertFloat, convertInt, getAudioDuration, getParsedText, md5
import traceback
import requests
import pandas as pd
import threading
import logging
from shutil import copy,rmtree

from utils.translateText import translate_text
logger = logging.getLogger(__name__)


from rest_framework.test import force_authenticate
from rest_framework.test import APIRequestFactory
from salesPage.views import SalesPageCopyView
from threading import Thread
from newImageEditor import models as newImageEditorModels
from urlShortner import models as urlShortnerModels
from backgroundclip import models as backgroundclipModels
from backgroundclip import serializers as backgroundclipSerializers



def getUserLibrarayAudioPath(id,user):
    try:
        _inst = FileUpload.objects.get(id=id,user=user)
        _audioP = _inst.convertAudioToWav()
        open('/home/govind/merge.txt','a').write(f"{_audioP}\n")
        if _audioP:
            return _audioP
        return _inst.media_file.path
    except:
        return None

def getAiAudioInst(soundInst,textData,user,isEnglishTextConversion=False):
    allAudioInfo = []
    allThread = []
    allInst = []
    for _textInst in textData:
        if isEnglishTextConversion:
            _textInst["text"] = translate_text(soundInst.voice_language.code,text=_textInst["text"])
        aiAudioInst,ct = AiAudio.objects.get_or_create(avatarSound=soundInst,text=_textInst["text"])
        if ct:
            aiAudioInst.user = user
            aiAudioInst.save()
        allAudioInfo.append({"id": aiAudioInst.id,"delay": _textInst["delay"]})
        _thread = Thread(target=aiGenerateSound, args=(aiAudioInst,True,))
        _thread.start()
        allInst.append(aiAudioInst)
        allThread.append(_thread)

    for ct in allThread:
        ct.join()
    
    _combineInst,ct = AiCombineAudio.objects.get_or_create(allAudioInfo=json.dumps(allAudioInfo))
    audioPath = None
    if ct:
        _combineInst.user = user
        _combineInst.save()
    else:
        if _combineInst.wav_sound:
            _audioPath = _combineInst.wav_sound.path
            if os.path.isfile(_audioPath):
                return (True, _combineInst.wav_sound.path)

    isSuccess =_combineInst.combineMultipleAiAudio(allInst,allAudioInfo,isWavThread=False)
    if isSuccess and _combineInst.wav_sound:
        audioPath = _combineInst.wav_sound.path
    return (isSuccess,audioPath)




AI_STATUS = (
    (0,'ERROR'),

    (2,'RUNNING'),
    (3,'PENDING'),

    (1,'COMPLETED'),
)

class AiTaskWithAudio(models.Model):
    
    uuid = models.UUIDField(default=uuid4, editable=False)
    audioHash = models.CharField(max_length=256)
    avatar_image = models.ForeignKey("appAssets.AvatarImages", on_delete=models.CASCADE)
    
    fullAudioPath = models.FileField(upload_to="newvideocreator/aiTask/audio",blank=True,null=True)

    start_frame = models.IntegerField(default=0)
    
    status = models.IntegerField(default= 3,choices=AI_STATUS)

    logs = models.CharField(null=True,blank=True,max_length=1000)
    totalOutputFrame = models.IntegerField(default=0)
    completedFrame = models.IntegerField(default=0)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ('audioHash', 'avatar_image','start_frame',)

    def getRootDir(self):
        _rootP = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/aiTask/audio")
        os.makedirs(_rootP,exist_ok=True)
        return _rootP
    
    def getAiVideoOutputPath(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/aiTask/imageSeq/",f"{self.uuid}")
        os.makedirs(_path,exist_ok=True)
        return os.path.join(_path,'aiTransparentVideo.webm')

    def getImageSeqDir(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/aiTask/imageSeq/",f"{self.uuid}")
        os.makedirs(_path,exist_ok=True)
        return _path

    def addAudio(self,audioPath):
        file_name = os.path.basename(audioPath)
        outputPath = os.path.join(self.getRootDir(),f"{self.id}_{file_name}")
        copy(audioPath,outputPath)
        self.fullAudioPath.name = outputPath.split(settings.MEDIA_ROOT)[1]
        open('/home/govind/text.log','a').write(f"{audioPath} {file_name} {outputPath} {outputPath.split(settings.MEDIA_ROOT)[1]}\n")
        self.save()


@receiver(models.signals.post_delete, sender=AiTaskWithAudio)
def auto_delete_file_AiTaskWithAudio(sender, instance, **kwargs):
    if instance.fullAudioPath:
        if os.path.isfile(instance.fullAudioPath.path):
            os.remove(instance.fullAudioPath.path)
    _imgSeqDir = instance.getImageSeqDir()
    if os.path.exists(_imgSeqDir) and os.path.isdir(_imgSeqDir):
        rmtree(_imgSeqDir)




class VideoTemplate(models.Model):
    # Custom fields
    name = models.CharField(max_length=250,blank=True,null=True,default='Untitled Video')

    hVideo = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE,blank=True,null=True,related_name='horizontal_video')
    vVideo = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE,blank=True,null=True,related_name='vertical_video')
    sVideo = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE,blank=True,null=True,related_name='square_video')

    isHuman = models.BooleanField(default=True)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        hVid = -1
        if self.hVideo:
            hVid = self.hVideo.id
        vVid = -1
        if self.vVideo:
            vVid = self.vVideo.id
        sVid = -1
        if self.sVideo:
            sVid = self.sVideo.id
        return f"{self.name} H: {hVid} S: {sVid} V: {vVid}"



AVATAR_AUDIO_GENERATED = (
    (0,'False'),
    (1,'True'),
    (2,'Blank'),
)


class AiVideoSceneGenerate(models.Model):

    aiTask = models.ForeignKey('AiTaskWithAudio',on_delete=models.SET_NULL,related_name='MainAiVideoSceneGenerate_aiTask',blank=True,null=True)
    videoCreator = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE,related_name='AiVideoSceneGenerate_TempVideoCreator')
    _mainVideoGenerate = models.ForeignKey('MainVideoGenerate',on_delete=models.CASCADE,related_name='AiVideoSceneGenerate_MainVideoGenerate',blank=True,null=True)

    sceneIndex = models.IntegerField(default=0)
    _order = models.IntegerField(default=0)
    isMergeTag = models.BooleanField(default=False)

    isAvatarAudioGenerated =  models.IntegerField(default= 0,choices=AVATAR_AUDIO_GENERATED)
    mergeTagValue = models.TextField(blank=True,null=True)

    avatarSound = models.FileField(upload_to="newvideocreator/scene/avatar_sound/",blank=True,null=True)
    isSceneAudioGenerated =  models.BooleanField(default=False)
    sceneAudio = models.FileField(upload_to="newvideocreator/scene/audio/",blank=True,null=True)
    avatarStartTime = models.FloatField(default=0)
    avatarTotalTime = models.FloatField(default=0)

    isAvatarVideoGenerated = models.BooleanField(default=False)

    isVideoGenerated = models.BooleanField(default=False)
    video = models.FileField(upload_to="newvideocreator/scene/video/",blank=True,null=True)
    thumbnail = models.ImageField(upload_to='newvideocreator/scene/thumbnail/',default='newvideocreator/thumbnail/default.jpg')

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['_order']
    
    def __str__(self):
        return f"{self.videoCreator.id} {self._mainVideoGenerate.id} {self.id}"
    
    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/scene/")
        os.makedirs(_path,exist_ok=True)
        return _path

    def getVideoPath(self):
        _videoPath = os.path.join(self.getCwd(),"video")
        os.makedirs(_videoPath,exist_ok=True)
        return os.path.join(_videoPath,f"{self._mainVideoGenerate.id}-{self.id}.mp4")

    def getVideoName(self):
        return f"newvideocreator/scene/video/{self._mainVideoGenerate.id}-{self.id}.mp4"

    def getThumbnailPath(self):
        _thumbnailPath = os.path.join(self.getCwd(),"thumbnail")
        os.makedirs(_thumbnailPath,exist_ok=True)
        return os.path.join(_thumbnailPath,f"{self._mainVideoGenerate.id}-{self.id}.jpeg")

    def getThumbnailName(self):
        return f"newvideocreator/scene/thumbnail/{self._mainVideoGenerate.id}-{self.id}.jpeg"

    def getSceneAudioPath(self):
        _audioPath = os.path.join(self.getCwd(),"audio")
        os.makedirs(_audioPath,exist_ok=True)
        return os.path.join(_audioPath,f"{self._mainVideoGenerate.id}-{self.id}.mp3")

    def getSceneAudioName(self):
        return f"newvideocreator/scene/audio/{self._mainVideoGenerate.id}-{self.id}.mp3"

    def getPreviousScene(self):
        if self._order>0:
            try:
                _inst = AiVideoSceneGenerate.objects.get(_mainVideoGenerate=self._mainVideoGenerate,_order=self._order-1)
                return (True,_inst)
            except:
                pass
        return (False,None)

    def sendJobToVideoRender(self):
        ## prepeare Data for video render
        
        if self.isVideoGenerated == False and self.isAvatarVideoGenerated and self.isSceneAudioGenerated:
            _avatarData = {'isAvatar': False}
            if self.aiTask:
                if self.aiTask.status==1:
                    _avatarData['isAvatar'] = True
                    _avatarData['avatarStartTime'] = self.avatarStartTime
                    _avatarData['totalFrames'] = self.aiTask.totalOutputFrame
                    _avatarData['imageSeqDir'] = self.aiTask.getImageSeqDir()

            _renderData = {
                "id": self.videoCreator.id,"sceneIndex": self.sceneIndex,"sceneInstId": self.id,
                "avatarInfo": _avatarData,"outputPath": self.getVideoPath(),"audioPath": self.getSceneAudioPath(),
                "avatarSoundDuration": self.avatarTotalTime
            }
            # get previous scene
            _isPrevSceneExist,_prevScene = self.getPreviousScene()
            if _isPrevSceneExist:
                _renderData["prevScene"] = {"avatarSoundDuration": _prevScene.avatarTotalTime}
                if _prevScene.aiTask and _prevScene.aiTask.status==1:
                    _renderData["prevScene"]['isAvatar'] = True
                    _renderData["prevScene"]['avatarStartTime'] = _prevScene.avatarStartTime
                    _renderData["prevScene"]['totalFrames'] = _prevScene.aiTask.totalOutputFrame
                    _renderData["prevScene"]['imageSeqDir'] = _prevScene.aiTask.getImageSeqDir()


            _mtag = json.loads(self._mainVideoGenerate.allMergeTag)
            if self._mainVideoGenerate.generationType and len(_mtag):
                _renderData['isPersonalized'] = True
                _renderData['mergeData'] = {'key': _mtag,'value': json.loads(self._mainVideoGenerate.mergeTagValue)}
            else:
                if self.videoCreator.objTagData and self.videoCreator.type==2:
                    _renderData['objTagData'] = json.loads(self.videoCreator.objTagData)[f"{self.sceneIndex}"]

            rabbitMQSendJob('newVideoCreatorJob',json.dumps(_renderData),durable=True)


    def onComplete(self,completedScene=0,totalScene=0):
        # send task to video rendering
        self.isAvatarVideoGenerated = True
        self.save()
        # update progress
        if totalScene>0:
            self._mainVideoGenerate.aiVideoProgress = int((completedScene/totalScene)*100)
            self._mainVideoGenerate.save()
            self._mainVideoGenerate.updateProgress()

        _isVideoProcessed = json.loads(self.videoCreator._videoData)["processed"][f"{self.sceneIndex}"]
        if _isVideoProcessed:
            self.sendJobToVideoRender()

        

    def onRenderComplete(self):
        self.isVideoGenerated = True
        self.video.name = self.getVideoName()
        self.save()
        # check if all Video Completed
        _allInst = self._mainVideoGenerate.aiSceneGenerate.all()
        _totalScene = _allInst.count()
        if _totalScene>0:
            _completed = 0
            allCompleted = True
            for _inst in _allInst:
                if not _inst.isVideoGenerated:
                    allCompleted = False
                else:
                    _completed += 1
            
            if allCompleted:
                self._mainVideoGenerate.onComplete()
            else:
                self._mainVideoGenerate.renderProgress = int((_completed/_totalScene)*100)
                self._mainVideoGenerate.save()
                self._mainVideoGenerate.updateProgress()

    def getRootDir(self):
        _rootP = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/scene/")
        os.makedirs(_rootP,exist_ok=True)
        return _rootP

    def addAiAudio(self,audioPath):
        file_name = os.path.basename(audioPath)
        outputPath = os.path.join(self.getRootDir(),"avatar_sound",f"{self.videoCreator.id}_{file_name}")
        copy(audioPath,outputPath)
        self.avatarSound.name = outputPath.split(settings.MEDIA_ROOT)[1]
        self.isAvatarAudioGenerated = True
        self.avatarTotalTime = getAudioDuration(outputPath)
        self.save()
    
    def getThumbnailData(self):
        _outputPath = self.getThumbnailPath()
        self.thumbnail.name = self.getThumbnailName()
        self.save()
        copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),_outputPath)
        return {"scene": self.sceneIndex,"outputPath": _outputPath}




VIDEO_CATEGORY = (
    (0,'Main'),
    (1,'Single Download'),
    (2,'Single Link'),
    (3,'Group Code'),
    (4,'Solo Code'),
)


EMAIL_GEN_TRACKER_TYPE = (
    (0,'SOLO'),
    (1,'BATCH')
)


class EmailGenTracker(models.Model):
    
    videoCreator = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE)
    _type = models.IntegerField(default=0,choices=EMAIL_GEN_TRACKER_TYPE)
    soloInst = models.ForeignKey("MainVideoGenerate",on_delete=models.CASCADE,blank=True,null=True)
    groupInst = models.ForeignKey("GroupHandler",on_delete=models.CASCADE,blank=True,null=True)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)


class GroupHandler(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    videoCreator = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE,related_name='grouphandler_video_creator')
    thumbnailInst = models.ForeignKey("newImageEditor.ImageCreator", on_delete=models.SET_NULL,blank=True,null=True)
    sharingPageData = models.TextField(blank=True,null=True)

    allMergeTag = models.TextField(default="[]",blank=True,null=True)
    mergeTagMap = models.TextField(blank=True,null=True)
    fileName = models.CharField(max_length=250,blank=True,null=True)
    csvFile = models.FileField(upload_to="newvideocreator/grouphandler/csv/",blank=True,null=True)
    originalFile = models.FileField(upload_to="newvideocreator/grouphandler/original/",blank=True,null=True)
    generatedFile = models.FileField(upload_to="newvideocreator/grouphandler/generated/",blank=True,null=True)
    isAdded = models.BooleanField(default=False)
    mailClient = models.IntegerField(default = -1)
    isValidated = models.BooleanField(default=False)

    status = models.IntegerField(default=3,choices=AI_STATUS)
    totalCount = models.IntegerField(default=0)
    generatedCount = models.IntegerField(default=0)

    _shortUrl = models.OneToOneField('urlShortner.CampaignUrlShortner',on_delete=models.SET_NULL,null=True,blank=True)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/grouphandler/")
        os.makedirs(_path,exist_ok=True)
        return _path

    def getCsvPath(self,filename):
        _path = os.path.join(self.getCwd(),"csv")
        os.makedirs(_path,exist_ok=True)
        return os.path.join(_path,filename)

    def getOriginalPath(self,filename):
        _path = os.path.join(self.getCwd(),"original")
        os.makedirs(_path,exist_ok=True)
        return os.path.join(_path,filename)

    def getGeneratedPath(self):
        _path = os.path.join(self.getCwd(),"generated")
        _filename = f"{self.id}.csv"
        os.makedirs(_path,exist_ok=True)
        return os.path.join(_path,_filename)

    def getCsvName(self,filename):
        return f"newvideocreator/grouphandler/csv/{filename}"

    def getOriginalName(self,filename):
        return f"newvideocreator/grouphandler/original/{filename}"

    def getGeneratedName(self):
        _filename = f"{self.id}.csv"
        return f"newvideocreator/grouphandler/generated/{_filename}"

    def generateCSVFile(self):
        try:
            _querySet = MainVideoGenerate.objects.filter(groupHandlerTracker=self)
            _mergeTag = json.loads(self.allMergeTag)
            _mergeTag += [["status","text"],["campaignUrl","text"]]
            _columnName = [i[0] for i in _mergeTag]

            finalData = []
            for _inst in _querySet:
                _rawData = json.loads(_inst.mergeTagValue)
                _rawData += [_inst.status,f"https://autovid.ai/p/{_inst.id}?email=video_creator"]
                finalData.append(_rawData)

            _df = pd.DataFrame(finalData, columns=_columnName)
            _df.to_csv(self.getGeneratedPath(),index=False)
            self.generatedFile = self.getGeneratedName()
            self.save()
            return True
        except:
            return False

    def updateProgress(self):
        # handle websocket
        _crntProgress = self.getProgress()
        commandData = {'id': self.videoCreator.id,'results': {"id": f"{self.id}","type": 3,"status": self.status,"progress": _crntProgress,"generatedCount": self.generatedCount,"totalCount": self.totalCount}}
        fire.eventFire(self.videoCreator.user,"videoEditor.progress.update",commandData)
        

    def getProgress(self):
        if self.status != 1 and self.totalCount>0:
            _generated = MainVideoGenerate.objects.filter(groupHandlerTracker=self,status=1)
            _error = MainVideoGenerate.objects.filter(groupHandlerTracker=self,status=0)
            _generatedC = _generated.count()
            _errorC = _error.count()
            _crntP = _generatedC+_errorC
            if self.totalCount == _crntP:
                self.status = 1
                self.generatedCount = self.totalCount
                self.save()
                return 100
            else:
                if self.generatedCount != _crntP:
                    self.generatedCount = _crntP
                    self.save()
                return int((self.generatedCount/self.totalCount)*100)
        return 100
    
    def addShortUrl(self):
        _sInst = None
        try:
            _sInst = urlShortnerModels.CampaignUrlShortner.objects.get(_type=3,mainId=f"{self.id}",_appType=1)
        except:
            _sInst = urlShortnerModels.CampaignUrlShortner(_type=3,mainId=f"{self.id}",_appType=1)
            _getSlug = _sInst.generateSlug()
            _sInst.slug = _getSlug
            _sInst.save()
        self._shortUrl = _sInst
        self.save()


@receiver(models.signals.post_delete, sender=GroupHandler)
def auto_delete_file_GroupHandler(sender, instance, **kwargs):
    if instance.csvFile:
        if os.path.isfile(instance.csvFile.path):
            os.remove(instance.csvFile.path)
    if instance.originalFile:
        if os.path.isfile(instance.originalFile.path):
            os.remove(instance.originalFile.path)


class MainVideoGenerate(models.Model):
    # Custom fields
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    videoCreator = models.ForeignKey('TempVideoCreator',on_delete=models.CASCADE,related_name='video_creator')
    sharingPageData = models.TextField(blank=True,null=True)
    
    video = models.FileField(upload_to="newvideocreator/mainvideo/video/",default='newvideocreator/mainvideo/default.mp4',blank=True)
    thumbnail = models.ImageField(upload_to='newvideocreator/mainvideo/thumbnail',default='newvideocreator/thumbnail/default.jpg')

    mergeTagValue = models.TextField(blank=True,null=True)
    allMergeTag = models.TextField(default="[]",blank=True,null=True)

    # selectedThumbnail = models
    aiSceneGenerate = models.ManyToManyField('AiVideoSceneGenerate')
    generationType =  models.IntegerField(default= 0,choices=VIDEO_CATEGORY)
    groupHandlerTracker = models.ForeignKey("GroupHandler",on_delete=models.CASCADE,blank=True,null=True)
    uniqueIdentity = models.CharField(max_length=250,blank=True,null=True)
    status = models.IntegerField(default=3,choices=AI_STATUS)

    isSoundGenerated = models.BooleanField(default=False)
    isSetupCompleted = models.BooleanField(default=False)
    audio = models.FileField(upload_to="newvideocreator/mainvideo/audio/",blank=True,null=True)

    renderProgress = models.IntegerField(default=0)
    aiVideoProgress = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)

    _shortUrl = models.OneToOneField('urlShortner.CampaignUrlShortner',on_delete=models.SET_NULL,null=True,blank=True)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.videoCreator.id}"

    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/mainvideo/")
        os.makedirs(_path,exist_ok=True)
        return _path
    
    def getCombineVideoTextPath(self):
        return os.path.join(self.getCwd(),f"{self.id}.txt")

    def updateProgress(self):
        self.progress = self.getProgress()
        self.save()
        if self.generationType != 3:
            commandData = {'id': self.videoCreator.id,'results': {"id": f"{self.id}","type": self.generationType,"status": self.status,"progress": self.progress}}
            if self.status == 1:
                if self.generationType == 0 or self.generationType==1:
                    commandData['results']['video'] = self.getVideoUrl()
                elif self.generationType == 2 or self.generationType == 4:
                    commandData["results"]["campaignUrl"] = self._shortUrl.getUrl()

            fire.eventFire(self.videoCreator.user,"videoEditor.progress.update",commandData)

    def setThumbnail(self):
        _thumbnailPath = self.getThumbnailPath()
        self.thumbnail.name = self.getThumbnailName()
        self.save()

        if self.videoCreator.thumbnailInst:
            _thumbnailInstP = self.videoCreator.thumbnailInst.thumbnail.path
            if os.path.exists(_thumbnailInstP):
                copy(_thumbnailInstP,_thumbnailPath)
            else:
                copy(self.videoCreator.thumbnail.path,_thumbnailPath)
            
            if self.generationType:
                _mtag = json.loads(self.allMergeTag)
                _renderData = {"id": self.videoCreator.thumbnailInst.id,"videoId": self.videoCreator.id,"isImage": True,"data": [{"scene": 0,"outputPath": _thumbnailPath}]}
                if self.videoCreator.thumbnailInst.isPersonalized:
                    _renderData['isPersonalized'] = True
                    _renderData['mergeData'] = {'key': _mtag,'value': json.loads(self.mergeTagValue)}
                    rabbitMQSendJob('setDraftThumbnail',json.dumps(_renderData),durable=True)
        else:
            copy(self.videoCreator.thumbnail.path,_thumbnailPath)

        return 1


    def getProgress(self):
        if self.status==1:
            return 100
        elif self.status==2:
            _approxPercentage = {"audio": 5,"aiVideo": 50,"renderVideo": 45}
            _progress = int(self.isSoundGenerated*_approxPercentage["audio"] + self.renderProgress*(_approxPercentage["renderVideo"]/100) + self.aiVideoProgress*(_approxPercentage["aiVideo"]/100))
            return _progress
        else:
            return 0

    def onAiComplete(self):
        self.aiVideoProgress = 100
        self.save()
        self.updateProgress()
        return True

    def onComplete(self,notCompleted=True):
        # do something
        #self.aiVideoProgress = 100
        # # combine all SceneInst and audio
        if notCompleted:
            combineAudioVideo(f"{self.id}")
            # combineVideoAtFileLevel(f"{self.id}")
            
        self.video.name = self.getVideoName()
        self.renderProgress = 100
        self.status = 1
        self.save()
        self.addShortUrl()
        
        self.updateProgress()
        # handle batch mail
        if self.groupHandlerTracker:
            self.groupHandlerTracker.updateProgress()

        if self.generationType==0:
            # add mode and duration
            _parseData = json.loads(self.videoCreator.parseData)
            _videoMode = _parseData.get("videoMode",0)
            _duration = _parseData.get("duration",3)
            _meta = {"type": "NON_AVATAR_VIDEO","duration":_duration,"id": f"{self.id}","videoId": f"{self.videoCreator.id}","name": f"{self.videoCreator.name}","userId": f"{self.videoCreator.user.id}"}
            # add to task
            if not _videoMode:
                #avatar mode
                _meta["type"] = "AVATAR_VIDEO"

            newVideoCreatorTask.addCreditTask.delay(_meta)

        
        # temp
        # _tmpD = json.loads(self.videoCreator.parseData)["avatarInfo"]
        # addAvatarSoundSample.moveFile(self.video.path,_tmpD["imageId"],_tmpD["audioId"])
        # newVideoCreatorTask.tempTask.delay(f"{self.videoCreator.id}")
        return True

    def getSoundPath(self):
        _soundP = os.path.join(self.getCwd(),'audio/')
        os.makedirs(_soundP,exist_ok=True)
        return os.path.join(_soundP,f"{self.id}.mp3")
    
    def getSoundName(self):
        return f"newvideocreator/mainvideo/audio/{self.id}.mp3"

    def getVideoPath(self):
        _soundP = os.path.join(self.getCwd(),'video/')
        os.makedirs(_soundP,exist_ok=True)
        return os.path.join(_soundP,f"{self.id}.mp4")
    
    def getVideoName(self):
        return f"newvideocreator/mainvideo/video/{self.id}.mp4"

    def getVideoUrl(self):
        return f"{settings.MEDIA_URL}{self.getVideoName()}"

    def getThumbnailPath(self):
        _soundP = os.path.join(self.getCwd(),'thumbnail/')
        os.makedirs(_soundP,exist_ok=True)
        return os.path.join(_soundP,f"{self.id}.jpeg")
    
    def getThumbnailName(self):
        return f"newvideocreator/mainvideo/thumbnail/{self.id}.jpeg"

    def generateVideo(self):
        if self.generationType==0:
            self.videoCreator.parseJsonData()
            newVideoCreatorTask.addVideoToGenerate.delay(f"{self.id}")
            return True
            # self.setDefaultMergeTag()
            # self.videoCreator.addDefaultSalesPage()
            # self.addSceneToAiTask()
            # self.saveAllThumbnail()
            # self.videoCreator.updateAllMergeTag()
            # newVideoCreatorTask.extractVideoFrames.delay({"videoId": f"{self.id}"})
        elif self.generationType==1:
            self.addSceneToAiTask()
        elif self.generationType==2:
            self.addSceneToAiTask()
        elif self.generationType==3:
            self.addSceneToAiTask()
        elif self.generationType==4:
            _inst,ct = EmailGenTracker.objects.get_or_create(videoCreator=self.videoCreator,_type=0,soloInst=self)
            self.addSceneToAiTask()

        self.setThumbnail()
        if not self.isSoundGenerated:
            newVideoCreatorTask.mainVideoAudioGenerate.delay(f"{self.id}")

    def saveAllThumbnail(self):
        if self.generationType==0:
            allInst = self.aiSceneGenerate.all()
            allData = []
            for _indx,_scInst in enumerate(allInst):
                _tmpData = _scInst.getThumbnailData()
                _tmpData["scene"] = _indx
                if _indx==0:
                    _tmpData["isCallback"] = True
                allData.append(_tmpData)

                _isJ,jsonData = self.videoCreator.getOnlyOneSceneJsonData(_indx)
                if _isJ:
                    _new,ct = newImageEditorModels.ImageCreator.objects.get_or_create(user=self.videoCreator.user,name=f"Scene {_indx+1}",jsonData=jsonData,_videoId = self.videoCreator.id,isAutoGenerated=True,isGenerated=True)
                    _new.thumbnail.name = _scInst.thumbnail.name
                    _new.save()
                    _new.onGenerate()
                    if _indx == 0:
                        move(self.videoCreator.thumbnail.path,_scInst.thumbnail.path)
                        self.videoCreator.thumbnail.name = _new.thumbnail.name
                        self.videoCreator.thumbnailInst = _new
                        self.videoCreator.save()

            rabbitMQSendJob('setDraftThumbnail',json.dumps({"id": self.videoCreator.id,"data": allData}),durable=True)

    def setDefaultMergeTag(self):
        allMTag = json.loads(self.videoCreator.mergeTag)
        allTagValue = []
        for ii in allMTag:
            allTagValue.append(ii[0][2:-2])
        self.mergeTagValue = json.dumps(allTagValue)
        
        self.save()

    def getSceneWiseMTagValue(self,sceneData,mTagValue):
        finalTagVal = {}
        for ii in sceneData["speechMergeTag"]:
            finalTagVal[f"{ii}_text"] = mTagValue[f"{ii}_text"]
        for ii in sceneData["textBoxMergeTag"]:
            finalTagVal[f"{ii}_text"] = mTagValue[f"{ii}_text"]
        for ii in sceneData["imageMergeTag"]:
            finalTagVal[f"{ii}_url"] = mTagValue[f"{ii}_url"]
        return finalTagVal

    def addSceneToAiTask(self):
        _mainInst = None
        if self.generationType==0:
            allMTag = json.loads(self.videoCreator.mergeTag)
        else:
            _mainInst = MainVideoGenerate.objects.get(videoCreator=self.videoCreator,generationType=0)
            allMTag = json.loads(self.allMergeTag)

            # if video is not personalized
            _videoMergeTag = json.loads(self.videoCreator.mergeTag)
            if len(_videoMergeTag)==0:
                # add scene from mainVideo (generationType==0) and generatedVideoMapping
                copy(_mainInst.video.path,self.getVideoPath())
                allAiScene = [_inst for _inst in _mainInst.aiSceneGenerate.all()]
                self.aiSceneGenerate.add(*allAiScene)
                self.isSoundGenerated = True
                self.isSetupCompleted = True
                self.aiVideoProgress = 100
                self.status = 1
                self.save()
                self.onComplete(notCompleted=False)
                return True

        finalMTag = {}
        
        mergeTagValue = json.loads(self.mergeTagValue)

        for n,_stag in enumerate(allMTag):
            finalMTag['_'.join(_stag)] = mergeTagValue[n]

        allAiScene = []

        getAllText = json.loads(self.videoCreator.parseData)
        allSceneIndex = getAllText["sceneArr"]
        allSceneData = getAllText["data"]
        _imageId = getAllText["avatarInfo"]["imageId"]
        
        _audioId = getAllText["avatarInfo"]["audioId"]
        for _ord,_sceneIndex in enumerate(allSceneIndex):
            _isImage = allSceneData[_sceneIndex]["isImage"]
            _isAudio = allSceneData[_sceneIndex]["isAudio"]
            _audioPath = allSceneData[_sceneIndex]["audioPath"]

            if self.generationType !=0 and len(allSceneData[_sceneIndex]["speechMergeTag"]):
                ## regenerate ai speech
                _textData = allSceneData[_sceneIndex]["textData"]
                allMTagReplace = {}
                for ii in allSceneData[_sceneIndex]["speechMergeTag"]:
                    allMTagReplace[ii] = finalMTag[f"{ii}_text"]
                _newTextData = []
                for ii in _textData:
                    _text = ii["text"]
                    for _ttag in allMTagReplace:
                        _text = _text.replace(_ttag,allMTagReplace[_ttag])
                    _newTextData.append({"text": _text,"delay": ii["delay"]})
                soundInst = AvatarSounds.objects.get(id=_audioId)
                isSuccess,audioPath = getAiAudioInst(soundInst,_newTextData,self.videoCreator.user)
                if isSuccess:
                    _audioPath = audioPath
                    _isAudio = True

            if len(allSceneData[_sceneIndex]["speechMergeTag"]) or len(allSceneData[_sceneIndex]["textBoxMergeTag"]) or len(allSceneData[_sceneIndex]["imageMergeTag"]):
                _mtag = self.getSceneWiseMTagValue(allSceneData[_sceneIndex],finalMTag)
                
                _videoSceneInst,ct = AiVideoSceneGenerate.objects.get_or_create(videoCreator=self.videoCreator,_mainVideoGenerate=self,sceneIndex=_sceneIndex,_order=_ord,isMergeTag=True,mergeTagValue=json.dumps(_mtag),avatarStartTime=allSceneData[_sceneIndex]["avatarStartTime"])
                
                if _isAudio:
                    if len(allSceneData[_sceneIndex]["speechMergeTag"]) or self.generationType == 0:
                        _videoSceneInst.addAiAudio(_audioPath)
                    else:
                        # get parent 
                        _isParent = AiVideoSceneGenerate.objects.filter(_mainVideoGenerate=self,videoCreator__mainVideoGenerate__generationType=0,sceneIndex=_sceneIndex)
                        if _isParent:
                            _isSceneInst = _isParent.first()
                            if _isSceneInst.avatarSound:
                                _videoSceneInst.avatarSound.name = _isSceneInst.avatarSound.name
                                _videoSceneInst.isAvatarAudioGenerated = True
                                _videoSceneInst.save()
                            else:
                                _videoSceneInst.addAiAudio(_audioPath)
                        else:
                            _videoSceneInst.addAiAudio(_audioPath)
                else:
                    _videoSceneInst.isAvatarAudioGenerated = 2
                    _videoSceneInst.save()
            else:
                _videoSceneInst,ct = AiVideoSceneGenerate.objects.get_or_create(videoCreator=self.videoCreator,_mainVideoGenerate=self,sceneIndex=_sceneIndex,_order=_ord,isMergeTag=False,avatarStartTime=allSceneData[_sceneIndex]["avatarStartTime"])

                #scene already generated
                if _mainInst:
                    try:
                        _mainSceneInst = _mainInst.aiSceneGenerate.get(sceneIndex=_sceneIndex)
                        _videoSceneInst.aiTask = _mainSceneInst.aiTask
                        _videoSceneInst.isAvatarAudioGenerated = _mainSceneInst.isAvatarAudioGenerated
                        _videoSceneInst.avatarSound.name = _mainSceneInst.avatarSound.name
                        _videoSceneInst.isSceneAudioGenerated = _mainSceneInst.isSceneAudioGenerated
                        _videoSceneInst.sceneAudio.name = _mainSceneInst.sceneAudio.name
                        _videoSceneInst.avatarTotalTime = _mainSceneInst.avatarTotalTime
                        _videoSceneInst.isAvatarVideoGenerated = _mainSceneInst.isAvatarVideoGenerated
                        _videoSceneInst.isVideoGenerated = _mainSceneInst.isVideoGenerated
                        _videoSceneInst.video.name = _mainSceneInst.video.name
                        _videoSceneInst.save()
                        allAiScene.append(_videoSceneInst)
                        continue
                    except:
                        pass

                if ct:
                    if _isAudio:
                        _videoSceneInst.addAiAudio(_audioPath)
                    else:
                        _videoSceneInst.isAvatarAudioGenerated = 2
                        _videoSceneInst.save()

            if _isAudio and _audioPath:
                if _isImage:
                    _avatarImageInst = AvatarImages.objects.get(id=_imageId)
                    # create AiAudioTask...
                    _mdHash = md5(_audioPath)
                    _aiTask,ct = AiTaskWithAudio.objects.get_or_create(audioHash=_mdHash,avatar_image=_avatarImageInst,start_frame=0)
                    if ct:
                        _aiTask.addAudio(_audioPath)
                    _videoSceneInst.aiTask = _aiTask
                    _videoSceneInst.save()

            allAiScene.append(_videoSceneInst)

        self.aiSceneGenerate.clear()
        self.aiSceneGenerate.add(*allAiScene)
        self.isSetupCompleted = True
        self.save()
        
    def addShortUrl(self):
        _sInst = None
        try:
            _sInst = urlShortnerModels.CampaignUrlShortner.objects.get(_type=2,mainId=f"{self.id}",_appType=1)
        except:
            _sInst = urlShortnerModels.CampaignUrlShortner(_type=2,mainId=f"{self.id}",_appType=1)
            _getSlug = _sInst.generateSlug()
            _sInst.slug = _getSlug
            _sInst.save()
        self._shortUrl = _sInst
        self.save()


THUMBNAIL_TYPE= (
    (0,'VIDEO_SCENE'),
    (1,'TEMPLATE'),
    (2,'MY_IMAGE'),
)

VIDEO_RATIO = (
    (0,"16:9"),
    (1,"1:1"),
    (2,"9:16"),
)

VIDEO_TYPE = (
    (0,'WITHOUT_MTAG'),
    (1,'AVATAR_MTAG'),
    (2,'WITHOUT_AVATAR_MTAG'),
    
)

class VideoEditorHistoryMaintainer(models.Model):
    videoCreator = models.ForeignKey("TempVideoCreator", on_delete=models.CASCADE)
    _updateData = models.TextField(blank=True,null=True)
    jsonData = models.TextField(blank=True,null=True)
    status = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"{self.videoCreator.id}"





class TempVideoCreator(models.Model):
    # Custom fields
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=250,blank=True,null=True,default='Untitled Video')
    jsonData = models.TextField(blank=True,null=True)
    parseData = models.TextField(blank=True,null=True)
    _videoData = models.TextField(blank=True,null=True)

    objTagData = models.TextField(blank=True,null=True)

    isPersonalized = models.BooleanField(default=False)
    mergeTag = models.CharField(default="[]",max_length=5000,blank=True,null=True)
    allMergeTag = models.TextField(default="[]",blank=True,null=True)

    type = models.IntegerField(default= 0,choices=VIDEO_TYPE)

    
    thumbnail = models.ImageField(upload_to='newvideocreator/thumbnail/',default='newvideocreator/thumbnail/default.jpg')
    mainVideoGenerate = models.ForeignKey('MainVideoGenerate', on_delete=models.SET_NULL,blank=True,null=True,related_name='main_video_generate')
    sharingPage = models.ForeignKey('salesPage.SalesPageEditor', on_delete=models.SET_NULL,blank=True,null=True,related_name='TempVideoCreator_SalesPageEditor')
    mailClient = models.ForeignKey("campaign.EmailClient", on_delete=models.CASCADE,default=1)

    ratio = models.IntegerField(default= 0,choices=VIDEO_RATIO)

    thumbnailType = models.IntegerField(default= 0,choices=THUMBNAIL_TYPE)
    thumbnailInst = models.ForeignKey("newImageEditor.ImageCreator", on_delete=models.SET_NULL,blank=True,null=True)

    generatedAt = models.DateTimeField(default=timezone.now)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['-id']

    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"newvideocreator/")
        return _path


    def getDefaultSharingPage(self):
        _query = SalesPageEditor.objects.filter(isPublic=True)
        if _query.count()>0:
            DEFAULT_PUBLIC_ID = 8
            _inst = _query.filter(publicId=DEFAULT_PUBLIC_ID)
            if _inst.count()>0:
                return _inst.first()
            else:
                return _query.first()
        return False

    def addDefaultSalesPage(self):
        if not self.sharingPage:
            try:
                _inst = SalesPageEditor.objects.get(user=self.user,isDefault=True,appType=1)
                self.sharingPage = _inst
                self.save()
                return True
            except:
                # create new one
                _defaultInst = self.getDefaultSharingPage()
                if _defaultInst:
                    factory = APIRequestFactory()
                    view = SalesPageCopyView.as_view()
                    request = factory.get(f'/api/salespage/{_defaultInst.id}/copy/?appType=1&video_id={self.id}')
                    force_authenticate(request, user=self.user)
                    response = view(request,_defaultInst.id)

                    try:
                        _Id = response.data['result']['id']
                        _inst = SalesPageEditor.objects.get(id=_Id)
                        _inst.name = "Default Page"
                        _inst.isDefault = True
                        _inst.isPublish = True
                        _inst.setMergeTag()
                        self.sharingPage = _inst
                        self.save()
                        return True
                    except Exception as e:
                        print(f"{response.data}, {e}")
                        logger.error(f"NewVideoCreator TempVideoCreator Models addDefaultSalesPage: {str(traceback.format_exc())}")
        
        return False

    def updateAllMergeTag(self):
        allTag = []
        allAdded = {}
        _videoTag = json.loads(self.mergeTag)
        try:
            for _tag in _videoTag:
                if not allAdded.get(f"{_tag[0]}_{_tag[1]}",None):
                    allAdded[f"{_tag[0]}_{_tag[1]}"] = True
                    allTag.append(_tag)
        except:
            pass
        try:
            _thumbnailTag = json.loads(self.thumbnailInst.mergeTag)
            for _tag in _thumbnailTag:
                if not allAdded.get(f"{_tag[0]}_{_tag[1]}",None):
                    allAdded[f"{_tag[0]}_{_tag[1]}"] = True
                    allTag.append(_tag)
        except:
            pass


        if self.sharingPage and self.sharingPage.mergeTag:
            try:
                _salespageTag = json.loads(self.sharingPage.mergeTag)
                for _tag in _salespageTag:
                    if not allAdded.get(f"{_tag}_text",None):
                        allAdded[f"{_tag}_text"] = True
                        allTag.append([_tag,"text"])
            except:
                pass
        self.allMergeTag = json.dumps(allTag)
        self.save()

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

    def getData(self):
        return json.loads(self.jsonData)

    def isVideo(self,obj):
        if obj["_Type"] == "video":
            return True
        elif obj["_Type"] == "background":
            _data = obj.get("_Data",None)
            if _data:
                _tab = _data.get("tab",None)
                if _tab == 2:
                    return True
        return False
    
    def isObjectVisible(self,objData):
        _hidden = objData.get('_Hidden',False)
        #_visible = objData.get('visible',False)
        return (not _hidden)

    def getAvatarInfo(self,jsonData):
        _avatarInfo = jsonData.get("currentAvatar",None)
        _avatarData = {"isImageId": False,"imageId": None,"isAudioId": False,"audioId": None}
        soundInst = None
        if _avatarInfo:
            _audio = _avatarInfo.get("audio",None)
            if _audio:
                _audioId = convertInt(_audio.get("id",None),None)
                if _audioId!=None:
                    try:
                        soundInst = AvatarSounds.objects.get(id=_audioId)
                        _avatarData['audioId'] = _audioId
                        _avatarData["isAudioId"] = True
                    except:
                        pass

            _image = _avatarInfo.get("image",None)
            if _image:
                _imageId = convertInt(_image.get("id",None),None)
                if _imageId!=None:
                    try:
                        _inst = AvatarImages.objects.get(id=_imageId)
                        _avatarData['imageId'] = _imageId
                        _avatarData["isImageId"] = True
                    except:
                        pass
        return (_avatarData,soundInst)

    def getMusicInfo(self,sceneData):
        _musicInfo = {"currentScene": {},"allScene": {},"video": []}
        elementData = sceneData["elements"]
        objects = sceneData["jsonData"]["objects"]
        for _obj in objects:
            _id = _obj.get('id',None)
            _type = _obj.get('_Type',None)
            _music = _obj.get('_Music',None)
            if _type == 'music' and _music:
                _mid = _music.get("id",None)
                _elementData = elementData.get(_id,'None')
                if _elementData and _mid:
                    _trimStart = _elementData.get("trimStart",0)
                    _trimEnd = _elementData.get("trimEnd",0)
                    _adjustLength = _elementData.get("adjustLength",1)
                    _volume = _obj.get("_Volume",1)
                    if _adjustLength==1:
                        _musicInfo["currentScene"][_mid] = {"id": _mid,"trimStart": _trimStart,"trimEnd": _trimEnd,"adjustLength": _adjustLength,"volume": _volume}
                    else:
                        _musicInfo["allScene"][_mid] = {"id": _mid,"trimStart": _trimStart,"trimEnd": _trimEnd,"adjustLength": _adjustLength,"volume": _volume}

            else:
                if self.isVideo(_obj) and self.isObjectVisible(_obj):
                    _vidObj = _obj.get("_Video",{})
                    _vidId = _vidObj.get("id",None)
                    _elementData = elementData.get(_id,'None')
                    if _vidObj and _vidId and _elementData:
                        _trimStart = _elementData.get("trimStart",0)
                        _trimEnd = _elementData.get("trimEnd",0)
                        _enterDelay = _elementData.get("enterDelay",0)
                        _stayTime = _elementData.get("stayTime",0)
                        _adjustLength = _elementData.get("adjustLength",1)
                        _volume = _obj.get("_Volume",1)
                        _musicInfo["video"].append({"id": _vidId,"stayTime": _stayTime,"enterDelay": _enterDelay,"trimStart": _trimStart,"trimEnd": _trimEnd,"adjustLength": _adjustLength,"volume": _volume,"_Type": _obj["_Type"]})

        return _musicInfo
    
    def getTotalSceneDuration(self,sceneData):
        totalSceneDuration = 0
        elementData = sceneData["elements"]
        objects = sceneData["jsonData"]["objects"]
        for _obj in objects:
            _id = _obj.get('id',None)
            _type = _obj.get('_Type',None)
            if _type!='music':
                _elementData = elementData.get(_id,'None')
                if _elementData:
                    _enterDelay = _elementData.get("enterDelay",0)
                    _stayTime = _elementData.get("stayTime",0)
                    _totalDuration = _enterDelay + _stayTime
                    totalSceneDuration = max(totalSceneDuration, _totalDuration)
        return totalSceneDuration

    def updateVideoData(self,_jsonData=None):
        jsonData = _jsonData
        if not jsonData:
            jsonData = self.getData()
        allSceneIndex = self.getSceneArray(jsonData["currentScene"])
        if not self._videoData:
            _videoInfo = {"videoInfo": {},"sceneWiseData": {},"sanimation":{},"processed": {}}
        else:
            try:
                _videoInfo = json.loads(self._videoData)
            except:
                _videoInfo = {"videoInfo": {},"sceneWiseData": {},"sanimation":{},"processed": {}}

        _frameExtractTaskList = []
        _videoInfo["isSceneAnimation"] = {}
        for _sceneIndex in allSceneIndex:
            _videoInfo["sceneWiseData"][_sceneIndex] = []
            if not _videoInfo["processed"].get(_sceneIndex,False):
                _videoInfo["processed"][_sceneIndex] = False

            _videoInfo["sanimation"][_sceneIndex] = False
            _sceneData = jsonData[_sceneIndex]["jsonData"]["objects"]
            for n,_obj in enumerate(_sceneData):
                if self.isVideo(_obj):
                    _Video = _obj.get("_Video",{})
                    if _Video:
                        _id = _Video.get("id",None)
                        if _id:
                            try:
                                _inst = backgroundclipModels.APISaveVideo.objects.get(id=_id)
                                _videoInfo["videoInfo"][_id] = backgroundclipSerializers.APISaveVideoServerSideSerializer(_inst).data
                                _videoInfo["sceneWiseData"][_sceneIndex].append(_id)
                                if not _inst.isVideoProcessed:
                                    _frameExtractTaskList.append(_inst)
                            except Exception as e:
                                pass

                _sanimation = jsonData[_sceneIndex].get("sanimation",{})
                if _sanimation:
                    _animationD = _sanimation.get("animationData",{})
                    if _animationD:
                        _videoInfo["isSceneAnimation"][_sceneIndex] = True
                        _loadAsset = _animationD.get("loadAsset",{})
                        if _loadAsset:
                            _id = _loadAsset.get("id",None)
                            try:
                                _inst = backgroundclipModels.APISaveVideo.objects.get(id=_id)
                                _videoInfo["videoInfo"][_id] = backgroundclipSerializers.APISaveVideoServerSideSerializer(_inst).data
                                _videoInfo["sceneWiseData"][_sceneIndex].append(_id)
                                _videoInfo["sanimation"][_sceneIndex] = _id
                                if not _inst.isVideoProcessed:
                                    _frameExtractTaskList.append(_inst)
                            except Exception as e:
                                pass

        return _videoInfo
        # self._videoData = json.dumps(_videoInfo)
        # self.save()

    def getVideoMode(self,jsonData):
        return jsonData.get("mode",0)


    def parseJsonData(self):
        jsonData = self.getData()
        self._videoData = json.dumps(self.updateVideoData(jsonData))
        _avatarInfo,soundInst = self.getAvatarInfo(jsonData)
        allSceneIndex = self.getSceneArray(jsonData["currentScene"])
        sceneData = {}
        allMergeTag = []
        allAdded = {}
        totalDuration = 0
        isAvatarMTag = False
        mergeTagSceneWiseWithId = {}
        for _sceneIndex in allSceneIndex:
            # speechType ("type","upload","record")=>type == text
            mergeTagSceneWiseWithId[_sceneIndex] = {"text": [],"image": []}
            sceneData[_sceneIndex] = {'isImage': False,"isAudio": False,"audioPath": None,"avatarStartTime": 0,"avatarStayTime": 0,"speechType": None,"textData": [],"speechMergeTag": [],"textBoxMergeTag": [],"imageMergeTag": [],"musicInfo": self.getMusicInfo(jsonData[_sceneIndex]),"totalSceneDuration": self.getTotalSceneDuration(jsonData[_sceneIndex])}
            totalDuration+=sceneData[_sceneIndex]["totalSceneDuration"]
            _speechMTag = []
            _sceneData = jsonData[_sceneIndex]["jsonData"]["objects"]
            _avatars = [d for d in _sceneData if d['_Type'] == 'avatar']
            if len(_avatars)>0:
                if _avatarInfo["isImageId"]:
                    _avatarHidden = _avatars[0].get("_Hidden",False)
                    _avatarVisible = _avatars[0].get("visible",True)
                    if (not _avatarHidden) and _avatarVisible:
                        sceneData[_sceneIndex]["isImage"] = True
                if jsonData[_sceneIndex]["speech"]["type"] == "type" and _avatarInfo["isAudioId"]:
                    sceneData[_sceneIndex]["speechType"] = "type"
                    _speechArr = json.loads(jsonData[_sceneIndex]["speech"]["arr"])
                    isTextExist = False
                    speechData=[]
                    speechParseData=[]
                    for _sr in _speechArr:
                        _dd = jsonData[_sceneIndex]["speech"].get("data",{})
                        _d = _dd.get(_sr,None)
                        if _d:
                            _text = _d.get("text","")
                            _delay = convertFloat(_d.get("delay",None))
                            speechData.append({"text": _text,"delay": _delay})
                            speechParseData.append({"text": getParsedText(_text),"delay": _delay})
                            if _text:
                                _speechMTag.extend(getParsedText(_text,onlyTag=True))
                                isTextExist = True
                    if not isTextExist:
                        sceneData[_sceneIndex]["isImage"] = False
                        sceneData[_sceneIndex]["isAudio"] = False
                    else:
                        sceneData[_sceneIndex]["textData"] = speechData
                        # generate audio
                        isSuccess,audioPath = getAiAudioInst(soundInst,speechParseData,self.user)
                        if isSuccess:
                            sceneData[_sceneIndex]['audioPath'] = audioPath
                            sceneData[_sceneIndex]["isAudio"] = True

                elif jsonData[_sceneIndex]["speech"]["type"] == "upload":
                    sceneData[_sceneIndex]["speechType"] = "upload"
                    _getSoundId = jsonData[_sceneIndex]["speech"].get("sound",None)
                    if _getSoundId:
                        _getSoundId = _getSoundId.get("id",None)
                        sceneData[_sceneIndex]['audioPath'] = getUserLibrarayAudioPath(_getSoundId,self.user)
                        sceneData[_sceneIndex]["isAudio"] = True

                elif jsonData[_sceneIndex]["speech"]["type"] == "record":
                    sceneData[_sceneIndex]["speechType"] = "record"
                    _getSoundId = jsonData[_sceneIndex]["speech"].get("sound",None)
                    if _getSoundId:
                        _getSoundId = _getSoundId.get("id",None)
                        sceneData[_sceneIndex]['audioPath'] = getUserLibrarayAudioPath(_getSoundId,self.user)
                        sceneData[_sceneIndex]["isAudio"] = True

                else:
                    sceneData[_sceneIndex]["isImage"] = False
                    sceneData[_sceneIndex]["isAudio"] = False
                    sceneData[_sceneIndex]["speechType"] = None

            if sceneData[_sceneIndex]["isAudio"]:
                try:
                    sceneData[_sceneIndex]["avatarStartTime"] = convertFloat(jsonData[_sceneIndex]["elements"][_avatars[0]["id"]]["enterDelay"])
                    sceneData[_sceneIndex]["avatarStayTime"] = convertFloat(jsonData[_sceneIndex]["elements"][_avatars[0]["id"]]["stayTime"])
                except:
                    pass


            sceneData[_sceneIndex]["speechMergeTag"] = list(set(_speechMTag))
            if len(sceneData[_sceneIndex]["speechMergeTag"]):
                isAvatarMTag = True

            for _tag in sceneData[_sceneIndex]["speechMergeTag"]:
                if not allAdded.get(f"{_tag}_text",None):
                    allAdded[f"{_tag}_text"] = True
                    allMergeTag.append([_tag,'text'])
            try:
                _allTextBoxMTag = []
                for d in _sceneData:
                    if d['_Type'] == 'text':
                        _alltexttag = getParsedText(d.get("text",""),onlyTag=True)
                        _allTextBoxMTag.extend(_alltexttag)
                        if len(_alltexttag):
                            mergeTagSceneWiseWithId[_sceneIndex]['text'].append({"id": d.get("id",""),"tags": _alltexttag}) 
                            
                sceneData[_sceneIndex]["textBoxMergeTag"] = list(set(_allTextBoxMTag))

                for _tag in sceneData[_sceneIndex]["textBoxMergeTag"]:
                    if not allAdded.get(f"{_tag}_text",None):
                        allAdded[f"{_tag}_text"] = True
                        allMergeTag.append([_tag,'text'])
            except:
                pass
            try:
                _crntImageTag = []
                for d in _sceneData:
                    _usedITag = d.get('_Variable',"")
                    if (d.get("type","") == 'image' and _usedITag and d.get('_haveMerge',False)):
                        _crntImageTag.append(_usedITag)
                        mergeTagSceneWiseWithId[_sceneIndex]['image'].append({"id": d.get("id",""),"tag": _usedITag})


                _allImgVar = list(set(_crntImageTag))
                _finalImageMTag = []
                for _var in _allImgVar:
                    if _var[:2] != "{{" and _var[-2:]!="}}":
                        _finalImageMTag.append("{{"+_var+"}}")
                    else:
                        _finalImageMTag.append(_var)
                    
                sceneData[_sceneIndex]["imageMergeTag"] = _finalImageMTag

                for _tag in sceneData[_sceneIndex]["imageMergeTag"]:
                    if not allAdded.get(f"{_tag}_url",None):
                        allAdded[f"{_tag}_url"] = True
                        allMergeTag.append([_tag,'url'])
            except:
                pass

        finalData = {"sceneArr": allSceneIndex,"data": sceneData,'avatarInfo': _avatarInfo,'videoMode': self.getVideoMode(jsonData),'duration': totalDuration}
        self.parseData = json.dumps(finalData)
        self.mergeTag = json.dumps(sorted(allMergeTag))
        if len(allMergeTag):
            self.isPersonalized = True
            if isAvatarMTag:
                self.type = 1
            else:
                self.type = 2
                self.objTagData = json.dumps(mergeTagSceneWiseWithId)
        self.generatedAt = timezone.now()
        self.save()
        return finalData

    def getOnlyOneSceneJsonData(self,sceneIndex):
        jsonData = self.getData()
        allSceneIndex = self.getSceneArray(jsonData["currentScene"])
        if len(allSceneIndex)<=sceneIndex:
            return (False,"Scene Index Out of Range.")
        try:
            _crntIndex = 0
            for n,_index in enumerate(allSceneIndex):
                if n!=sceneIndex:
                    jsonData.pop(_index)
                else:
                    _crntIndex = _index
            jsonData[0] = jsonData.pop(_crntIndex)
            jsonData["currentScene"] = {"sceneArr": "[0]","arr": "[0]"}
            return (True,json.dumps(jsonData))
            
        except Exception as e:
            return (False,f"Error Occured {e}")

    # copy json data for other id
    def changeJsonDataId(self,newId):
        try:
            _jsonData = json.loads(self.jsonData)
            allSceneIndex = self.getSceneArray(_jsonData["currentScene"])
            for _sceneIndex in allSceneIndex:
                _sceneData = _jsonData[_sceneIndex]["jsonData"]["objects"]
                for _sceneObj in _sceneData:
                    _link = _sceneObj.get('_Link',None)
                    if _link:
                        _ymp = _link.split('/')
                        _ymp[2] = f"{newId}"
                        _sceneObj["_Link"] = '/'.join(_ymp)#_link.replace(f"{self.id}",f"{newId}")
            return (True,json.dumps(_jsonData))
        except Exception as e:
            logger.error(f"NewVideoCreator Models changeJsonDataId: {str(traceback.format_exc())}")
            return (False,None)

    def getAvatarSound(self,jsonData,sceneIndex):
        _data = {'avatar_image': AvatarImages.objects.first().id,'avatar_sound': AvatarSounds.objects.first().id}
        try:
            _data = {'avatar_image': jsonData["currentAvatar"]["audio"]["id"],'avatar_sound': jsonData["currentAvatar"]["image"]["id"]}
        except:
            pass
        return _data

    def getAllSceneText(self):
        sceneText = {}
        try:
            _jsonData = json.loads(self.jsonData)
            allSceneIndex = self.getSceneArray(_jsonData["currentScene"])
            for _sceneIndex in allSceneIndex:
                sceneText[_sceneIndex] = []
                _sceneData = _jsonData[_sceneIndex]["jsonData"]["objects"]
                _avatarData = self.getAvatarSound(_jsonData,_sceneIndex)
                for _sceneObj in _sceneData:
                    print(_sceneObj["_Type"], _sceneObj["visible"])
                    if _sceneObj["_Type"] == "avatar" and _sceneObj["visible"]:
                        _sceneData = _jsonData[_sceneIndex]["speech"]
                        print(_sceneData)
                        _speechArrIndex = json.loads(_sceneData["arr"])
                        _startTime = 0
                        for _index in _speechArrIndex:
                            _crntData = _sceneData["data"][_index]
                            sceneText[_sceneIndex].append({"text": _crntData["text"],"delay": _crntData["delay"],"duration": _crntData["duration"],"startTime": _startTime,"avatar_image": _avatarData["avatar_image"],"avatar_sound": _avatarData["avatar_sound"]})
                            _startTime += _crntData["delay"] + _crntData["duration"]
        except Exception as e:
            print("Error in Text Parse: ",e)
        return sceneText

    def isValidUser(user,pk):
        try:
            _inst = TempVideoCreator.objects.get(pk=pk)
            if _inst.user.id == user.id:
                return (True,_inst)
            else:
                _tmp = VideoTemplate.objects.filter(Q(hVideo=_inst) | Q(vVideo=_inst) | Q(sVideo=_inst))
                if _tmp.count()>0:
                    return (True,_inst)
        except:
            pass
        return (False,None)

    def getThumbnailPath(self):
        _filename = f"{uuid4()}.jpeg"
        _path = os.path.join(self.getCwd(),"thumbnail")
        os.makedirs(_path,exist_ok=True)
        return (os.path.join(_path,_filename),f"newvideocreator/thumbnail/{_filename}")


    def updateDraftThumbnail(self,scene=0):
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
            outputPath = outputPath.replace(uuidName,f"{uuid4()}.jpeg")
            copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)
            self.thumbnail = outputPath.split(settings.MEDIA_ROOT)[1]
            self.save()
        rabbitMQSendJob('setDraftThumbnail',json.dumps({"id": self.id,"data": [{"scene": scene,"outputPath": outputPath}]}),durable=True)

    def update_jsonData(self,newData):
        _url = settings.NODE_SERVER_BASE_URL + f"/newvideocreate/{self.id}/"
        _data = json.dumps({"jsonData": newData,"isImage": False})
        _r = requests.put(_url,data=_data,headers={'Content-Type': 'application/json'})
        _resData = None
        try:
            _resData = _r.json()
        except:
            _resData = _r.content

        # dump data
        _i = TempVideoCreator.objects.get(id=self.id)
        _inst,ct = VideoEditorHistoryMaintainer.objects.get_or_create(videoCreator=self,_updateData=newData,jsonData=_i.jsonData,status=_r.status_code)

        return (_r.status_code,_resData)

    def checkUploadUrlPresent(user,filename):
        allInst = TempVideoCreator.objects.filter(user=user,jsonData__contains=filename)
        return allInst.count()
    
    def updateAvatarSound(self,soundId):
        jsonData = self.getData()
        jsonData["currentAvatar"]["audio"]["id"] = soundId
        self.jsonData = json.dumps(jsonData)
        self.save()
        return True


def globalDeleteSharingPage():
    _querySet = TempVideoCreator.objects.filter(sharingPage=None)
    for _q in _querySet:
        _res = _q.addDefaultSalesPage()
    return 1


def setDefaultThumbnail(_thumbnailInst,request):
    _allInst = TempVideoCreator.objects.filter(thumbnailInst=_thumbnailInst)
    for _inst in _allInst:
        try:
            _iinst = newImageEditorModels.ImageCreator.objects.get(_videoId=_inst.id,name=f"Scene 1")
            _inst.thumbnailInst = _iinst
            _inst.thumbnailType = 0
            _inst.save()
        except:
            pass
    return 1



VIDEO_ANIMATION_TYPE = (
    (0,'IN_OUT'),
    (1,'INPLACE'),
)

class VideoAnimation(models.Model):
    # Custom fields
    name = models.CharField(max_length=100)
    url = models.FileField(upload_to="newvideocreator/animations/",default="newvideocreator/animations/default.svg",blank=True)
    exitSrc = models.FileField(upload_to="newvideocreator/animations/",blank=True,null=True)
    animationData = models.CharField(max_length=5000,blank=True,null=True)
    category = models.IntegerField(default= 0,choices=VIDEO_ANIMATION_TYPE)
    _order = models.IntegerField(default=0)


    class Meta:
        ordering = ['-_order','name']

    def __str__(self):
        return self.name



TEXT_ANIMATION_TYPE = (
    (0,'Character'),
    (1,'Word'),
    (2,'Line'),
)

class TextAnimation(models.Model):
    # Custom fields
    name = models.CharField(max_length=100)
    src = models.FileField(upload_to="newvideocreator/animations/",default="newvideocreator/animations/default.svg",blank=True)
    animationData = models.CharField(max_length=5000,blank=True,null=True)
    category = models.IntegerField(default= 0,choices=TEXT_ANIMATION_TYPE)
    _order = models.IntegerField(default=0)


    class Meta:
        ordering = ['-_order','name']

    def __str__(self):
        return self.name


SCENE_ANIMATION_TYPE = (
    (0,'Animation'),
    (1,'Overlay'),
)

class VideoSceneAnimation(models.Model):
    # Custom fields
    name = models.CharField(max_length=100)
    src = models.FileField(upload_to="newvideocreator/animations/",default="newvideocreator/animations/default.svg",blank=True)
    sample = models.FileField(upload_to="newvideocreator/animations/sample/",default="newvideocreator/animations/sample/sample.mp4",blank=True)
    animationData = models.CharField(max_length=5000,blank=True,null=True)
    category = models.IntegerField(default= 0,choices=SCENE_ANIMATION_TYPE)
    _order = models.IntegerField(default=0)


    class Meta:
        ordering = ['-_order','category','name']

    def __str__(self):
        return self.name

'''
Animation Variable
CANVAS_HEIGHT
CANVAS_WIDTH
OBJECT_{property} e.g => OBJECT_scaleX
'''


class VideoFilter(models.Model):
    # Custom fields
    name = models.CharField(max_length=100)
    url = models.FileField(upload_to="newvideocreator/filter/",blank=True)
    data = models.CharField(max_length=5000,blank=True,null=True)
    _order = models.IntegerField(default=0)

    class Meta:
        ordering = ['-_order','name']

    def __str__(self):
        return self.name

FONT_STYLE = (
    (0,"normal"),
    (1,"italic"),
)
FONT_WEIGHT = (
    (0,"normal"),
    (1,"bold"),
)
FONT_WEIGHT_DICT = {ii[0]:ii[1] for ii in FONT_WEIGHT}
FONT_STYLE_DICT = {ii[0]:ii[1] for ii in FONT_STYLE}

class FontConfig(models.Model):
    #name = models.CharField(max_length=100)
    fontUrl = models.FileField(upload_to="newvideocreator/fonts/",blank=True)
    style=models.IntegerField(default=0,choices=FONT_STYLE)
    weight=models.IntegerField(default=0,choices=FONT_WEIGHT)
    #fontConfig = models.CharField(max_length=1000,blank=True,null=True)

    def __str__(self):
        _name = f"{self.id}"
        _query = self.fontfamily_set.all()
        if _query.count()>0:
            _name = _query.first().name
        return f"{_name} {FONT_STYLE_DICT[self.style]} {FONT_WEIGHT_DICT[self.weight]}"


class FontFamily(models.Model):
    name = models.CharField(max_length=100)
    fonts = models.ManyToManyField("FontConfig",blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"
