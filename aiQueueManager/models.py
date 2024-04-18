from os import path
from videoAutomation.settings import BASE_DIR
from django.db import models
from django.contrib.auth import get_user_model
from appAssets.models import AvatarImages,AvatarSounds
from userlibrary.models import FileUpload
from django.core.files.base import ContentFile
from django.conf import settings
import os,cv2,json
import pandas as pd
import numpy as np
from tqdm import tqdm
from pathlib import Path
from django.db.models.signals import post_save
from django.dispatch import receiver
import re
import shutil
from uuid import uuid1,uuid4
import librosa
from utils.imageProcessing import cropCenter
from threading import Thread
import time
import subprocess
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob

from shutil import copy
from aiAudio.models import AiAudio
from utils.translateText import translate_text

BASE_DIR = settings.BASE_DIR

AI_STATUS = (
    (0,'ERROR'),

    (2,'AI_RUNNING'),
    (3,'PENDING'),

    (1,'COMPLETED'),
)

class AiTask(models.Model):
        
    text = models.CharField(max_length=50000)
    avatar_image = models.ForeignKey(AvatarImages, on_delete=models.CASCADE)
    avatar_sound = models.ForeignKey(AvatarSounds, on_delete=models.CASCADE)

    start_frame = models.IntegerField(default=0)
    
    status = models.IntegerField(default= 3,choices=AI_STATUS)

    output = models.CharField(blank=True,max_length=1000)
    totalOutputFrame = models.IntegerField(default=0)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.text[:20]}..."

    def getAiVideoOutputPath(self):
        return os.path.join(self.getcwd(),'aiTransparentVideo.webm')

    
    def isGeneratedVideo(self):
        _videoPath = self.getAiVideoOutputPath()
        if os.path.isfile(_videoPath):
            return True
        else:
            return False


    def getSquareData(self):
        side = self.avatar_image.sqSide
        x = self.avatar_image.sqX
        y = self.avatar_image.sqY
        return (x,y,x+side,y+side)
    
    def getAiPosition(self):
        positionX,positionY = (self.avatar_image.faceSwapPositionX,self.avatar_image.faceSwapPositionY)
        scale = self.avatar_image.faceSwapScale
        newSize = 512*scale
        prvPosX,prvPosY = (-256*scale,-256*scale)

        ix,iy = (positionX+prvPosX,positionY+prvPosY)
        ixf,iyf = round(ix+newSize),round(iy+newSize)
        ix,iy = round(ix),round(iy)
        if iy<0:
            iy = 0
        return (ix,iy,ixf,iyf)

    # get parent working directory
    def getcwd(self):
        try:
            tempDir = os.path.join(BASE_DIR,f'private_data/generated/{self.id}/')
            os.makedirs(tempDir,exist_ok=True)
            return tempDir
        except:
            tempDir = os.path.join(BASE_DIR,f'private_data/generated/{self.id}/')
            os.makedirs(tempDir,exist_ok=True)
            return tempDir
    
    def getFaceSwapDir(self):
        faceDir = os.path.join(self.getcwd(),'aiOutput/')
        os.makedirs(faceDir,exist_ok=True)
        return faceDir

    def generateSound(self,forceReload=False,convertEnglishToLanguage=False):
        parentDir = self.getcwd()
        output_name = os.path.join(parentDir,'sound.wav')
        if self.text:
            if os.path.isfile(output_name) and not forceReload:
                if self.totalOutputFrame <=0:
                    try:
                        totalF = librosa.get_duration(filename=output_name) * settings.VIDEO_DEFAULT_FPS
                        self.totalOutputFrame = totalF
                        self.save()
                    except:
                        pass
                return True
            else:
                finalText = None
                if convertEnglishToLanguage:
                    finalText = translate_text(self.avatar_sound.voice_language.code,text=self.text)
                else:
                    finalText = self.text

                aiAudioInst,ct = AiAudio.objects.get_or_create(avatarSound=self.avatar_sound,text=finalText)
                if forceReload:
                    ct = True
                if not (ct==False and aiAudioInst.isGenerated):
                    ## generate audio
                    TOTAL_TRIES = 3
                    isGenerated = False
                    message = None
                    for _ in range(TOTAL_TRIES):
                        outputPath = aiAudioInst.getcwd()
                        _soundname = f"{uuid4()}.mp3"
                        audioPath = os.path.join(outputPath,_soundname)
                        isSuccess,message = aiAudioInst.avatarSound.generateSound(aiAudioInst.text,audioPath)
                        if isSuccess:
                            aiAudioInst.sound.name = aiAudioInst.getModelSoundPath() + _soundname
                            aiAudioInst.isGenerated = True
                            aiAudioInst.save()
                            isGenerated = True
                            break
                    if not isGenerated:
                        self.status = 0
                        self.output = json.dumps({"message": message,"type": "sound"})
                        self.save()
                        return False


                copy(aiAudioInst.sound.path,output_name)
                totalF = librosa.get_duration(filename=aiAudioInst.sound.path) * settings.VIDEO_DEFAULT_FPS
                self.totalOutputFrame = totalF
                self.save()
                return True

        self.status = 1
        self.totalOutputFrame = 1
        self.save()
        return True

    def faceSwapFullBody(self):
        try:
            parentDir = self.getcwd()
            outputDir = self.getFaceSwapDir()

            currentVideo = cv2.VideoCapture(os.path.join(parentDir,'ai-output.avi'))

            avatarParentDir = self.avatar_image.getcwd()
            withoutSwapDir = os.path.join(avatarParentDir,'fullbody/without_swap/')
            maskDir = os.path.join(avatarParentDir,'fullbody/mask/')

            isCSV = True
            try:
                postionData = pd.read_csv(os.path.join(avatarParentDir,'fullbody/position.csv')) 
            except:
                isCSV = False       
            positionX,positionY = (self.avatar_image.faceSwapPositionX,self.avatar_image.faceSwapPositionY)
            scale = self.avatar_image.faceSwapScale
            anchorPointX,anchorPointY = (self.avatar_image.faceSwapAnchorPointX*scale,self.avatar_image.faceSwapAnchorPointY*scale)
            newSize = 512*scale
            allImgSeqName = sorted(os.listdir(withoutSwapDir))
            allImgSeqMask = sorted(os.listdir(maskDir))[self.start_frame:self.totalOutputFrame+self.start_frame]
            for fileName,frame_indx in tqdm(enumerate(allImgSeqName[self.start_frame:self.totalOutputFrame+self.start_frame])):
                if isCSV == False:
                    prvPosX,prvPosY = (-256*scale,-256*scale)
                else:
                    posIndex = int(frame_indx.split('.')[0])
                    prvPosX,prvPosY = ((postionData['X'].at[posIndex]-256)*scale,(postionData['Y'].at[posIndex]-256)*scale)
                ix,iy = (positionX+prvPosX-anchorPointX,positionY+prvPosY-anchorPointY)
                ixf,iyf = round(ix+newSize),round(iy+newSize)
                ix,iy = round(ix),round(iy)

                dsti = cv2.imread(os.path.join(withoutSwapDir,frame_indx),cv2.IMREAD_UNCHANGED)
                

                '''current_body_mask_path = os.path.join(maskDir,frame_indx)
                if os.path.exists(current_body_mask_path):
                    src_mask = cv2.imread(current_body_mask_path,cv2.IMREAD_GRAYSCALE)
                else:
                    dsti_gray = cv2.cvtColor(dsti, cv2.COLOR_BGR2GRAY)
                    dstf = settings.DLIB_DETECTOR(dsti_gray)[0]
                    dstlandm = settings.DLIB_PREDICTOR(dsti_gray, dstf)

                    dlandmarks_points = []
                    for n in range(0, 68):
                        x = dstlandm.part(n).x
                        y = dstlandm.part(n).y
                        dlandmarks_points.append((x, y))
                    dpoints = np.array(dlandmarks_points, np.int32)
                    dconvexhull = cv2.convexHull(dpoints)

                    src_mask = np.zeros(dsti_gray.shape, np.uint8)
                    tmp=cv2.fillConvexPoly(src_mask, dconvexhull, 255)
                    if self.avatar_image.id==5:
                        src_mask = cv2.erode(src_mask, np.ones((6, 6), np.uint8), cv2.BORDER_REFLECT,iterations = 2) 
                    cv2.imwrite(current_body_mask_path,src_mask)
                
                dst_mask = cv2.bitwise_not(src_mask)
                smask = np.zeros(dsti.shape, np.uint8)
                ret,frame = currentVideo.read()
                resizeAiFace = cv2.resize(cv2.cvtColor(frame,cv2.COLOR_BGR2BGRA),(ixf-ix,iyf-iy))
                if iy>=0:
                    smask[iy:iyf,ix:ixf] = resizeAiFace
                else:
                    iy *= -1
                    smask[0:iyf,ix:ixf] = resizeAiFace[iy:,:]
                src_mm = cv2.bitwise_and(smask, smask, mask = src_mask)
                dst_mm = cv2.bitwise_and(dsti, dsti, mask = dst_mask)

                fimg = np.array(np.add(src_mm,dst_mm),dtype='uint8')'''
                ret,frame = currentVideo.read()
                if self.avatar_image.id==5 or self.avatar_image.id==4:
                    faceMask = cv2.imread(os.path.join(maskDir,allImgSeqMask[fileName]),cv2.IMREAD_UNCHANGED)[:,:,3]
                    faceMask = cv2.cvtColor(cv2.resize(faceMask,(ixf-ix,iyf-iy)),cv2.COLOR_GRAY2BGR)/255
                    resizeAiFace = cv2.resize(frame,(ixf-ix,iyf-iy))
                    resizeAiFace = np.uint8(resizeAiFace*(faceMask))
                    if iy>=0:
                        aiFaceMask = np.uint8(dsti[iy:iyf,ix:ixf][:,:,:3]*(1-faceMask))
                        dsti[iy:iyf,ix:ixf][:,:,:3] = np.array(np.add(resizeAiFace,aiFaceMask),dtype='uint8')
                        
                    else:
                        iy *= -1
                        aiFaceMask = np.uint8(dsti[0:iyf,ix:ixf][:,:,:3]*(1-faceMask))
                        dsti[0:iyf,ix:ixf][:,:,:3] = np.array(np.add(resizeAiFace,aiFaceMask),dtype='uint8')
                else:
                    resizeAiFace = cv2.resize(frame,(ixf-ix,iyf-iy))

                    if iy>=0:
                        aiFaceMask = dsti[iy:iyf,ix:ixf][:,:,3]
                        aiFaceMask = cv2.cvtColor(aiFaceMask,cv2.COLOR_GRAY2BGR)
                        dsti[iy:iyf,ix:ixf][:,:,:3] = np.uint8(resizeAiFace*(aiFaceMask/255))
                        
                    else:
                        iy *= -1
                        aiFaceMask = dsti[0:iyf,ix:ixf][:,:,3]
                        aiFaceMask = cv2.cvtColor(aiFaceMask,cv2.COLOR_GRAY2BGR)
                        dsti[0:iyf,ix:ixf][:,:,:3] = np.uint8(resizeAiFace[iy:,:]*(aiFaceMask/255))
                cv2.imwrite(os.path.join(outputDir,f"{str(fileName).zfill(5)}.png"),dsti)

            self.status = 5
            self.save()
        except Exception as e:
            self.status = 0
            self.output = json.dumps({"message": str(e),"type": "face_swap"})
            self.save()


from django.core.validators import MaxValueValidator, MinValueValidator

class Colors(models.Model):

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    colors = models.CharField(max_length=1000,null=True,blank=True,default="")

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)



    def setColors(self,colors):
        validColors = []
        for color in colors.split(","):
            try:
                validColors.append(validate_color(color))
            except:
                pass
        self.colors = ','.join(validColors)
        self.save()

    def getColors(self):
        return [color for color in self.colors.split(",") if color]

    

class MergeTag(models.Model):

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    value = models.CharField(max_length=100)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-updated']
        unique_together = ('user', 'name',)



class SnapshotUrl(models.Model):
    # Custom fields
    singleScene = models.ForeignKey('VideoRenderSingleScene', on_delete=models.CASCADE)
    url = models.CharField(max_length=250)

    image = models.ImageField(upload_to='userlibrary/snapshot/',blank=True)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.url[:30]}..."


class VideoGradientColor(models.Model):
    
    name = models.CharField(max_length=200)
    media_file = models.ImageField(upload_to='aiQueueManager/VideoGradientColor/',default = 'aiQueueManager/VideoGradientColor/default.jpg')
    media_thumbnail = models.ImageField(upload_to='aiQueueManager/VideoGradientColor/',default = 'aiQueueManager/VideoGradientColor/default.jpg',null=True,blank=True)
    orderId = models.IntegerField(default=0)

    class Meta:
        ordering = ['orderId']

    def __str__(self):
        return self.name


class VideoThemeTemplate(models.Model):
    
    name = models.CharField(max_length=200)
    
    thumbnail = models.ImageField(upload_to='videotemplate/thumbnail/')
    filePreview = models.FileField(upload_to='videotemplate/file/',blank=True,null=True)

    config = models.CharField(max_length=1000,blank=True,null=True)

    orderId = models.IntegerField(default=0)

    class Meta:
        ordering = ['orderId']

    def __str__(self):
        return self.name
        

    


PRS_CATEGORY = (
    (0,'FULL'),
    (1,'CIRCLE'),
    (2,'SQUARE')
)

PRS_POSITION = (
    (0,'MIDDDLE_LEFT'),
    (1,'MIDDLE_CENTER'),
    (2,'MIDDLE_RIGHT'),
    (3,'BOTTOM_LEFT'),
    (4,'BOTTOM_CENTER'),
    (5,'BOTTOM_RIGHT')
)

BG_VIDEO_TYPE = (
    (0,'COLOR'),
    (1,'API_IMAGE'),
    (2,'UPLOAD_IMAGE'),
    (3,'API_VIDEO'),
    (4,'UPLOAD_VIDEO'),
    (5,'SNAPSHOT'),
    (6,'GRADIENT'),

)

PRS_BG_TYPE = (
    (0,'COLOR'),
    (1,'API_IMAGE'),
    (2,'UPLOAD_IMAGE'),
    (6,'GRADIENT'),
)

MUSIC_TYPE = (
    (-1,'PREVIOUS_CONTINUE'),
    (0,'DISABLED'),
    (1,'ENABLED'),
)


from django.core.exceptions import ValidationError

def validate_color(value):
    if value[0]!='#':
        value="#"+value
    match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value)
    if match:
        return value
    else:
        raise ValidationError("Hex Color is not Valid (eg #FFFFFF).")


class VideoRenderSingleScene(models.Model):
    
    text = models.CharField(max_length=5000,blank=True,null=True)
    videoThemeTemplate = models.ForeignKey(VideoThemeTemplate,on_delete=models.CASCADE)
    videoThemeTemplateData = models.TextField(default='',null=True,blank=True)

    bgVideoType = models.IntegerField(default= 0,choices=BG_VIDEO_TYPE)
    bgVideoID = models.IntegerField(blank=True,null=True)
    bgColor = models.CharField(max_length=10,blank=True,null=True,validators =[validate_color])
    isSnapshotMergeTag = models.BooleanField(default=False)
    snapshotData = models.ForeignKey(SnapshotUrl,blank=True,null=True,on_delete=models.SET_NULL,related_name='snapshotHistory')
    
    prsCategory = models.IntegerField(default= 0,choices=PRS_CATEGORY)
    prsPosition = models.IntegerField(default= 0,choices=PRS_POSITION)
    
    prsBgType = models.IntegerField(default= 0,choices=PRS_BG_TYPE)
    prsBgImageId = models.IntegerField(blank=True,null=True)
    prsBgColor = models.CharField(max_length=10,blank=True,null=True,validators =[validate_color])

    isLogo = models.BooleanField(default=False)
    logo = models.ForeignKey(FileUpload,blank=True,null=True,on_delete=models.SET_NULL,related_name='logo')

    isMusic = models.IntegerField(default= 0,choices=MUSIC_TYPE)
    music = models.ForeignKey(FileUpload,blank=True,null=True,on_delete=models.SET_NULL,related_name='music')
    
    aitask = models.ForeignKey(AiTask,on_delete=models.SET_NULL,blank=True,null=True)

    
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.text[:20]}..."

    def getcwd(self):
        tempDir = os.path.join(BASE_DIR,f'private_data/videoSingleScene/{self.id}/')
        os.makedirs(tempDir,exist_ok=True)
        return tempDir
        
    def getBgVideoSeq(self):
        tempDir = os.path.join(BASE_DIR,f'private_data/videoSingleScene/{self.id}/bgImgSeq')
        os.makedirs(tempDir,exist_ok=True)
        return tempDir

    def getBgVideoSeqPublicPath(self):
        tempDir = os.path.join(BASE_DIR,f'uploads/videoSingleScene/{self.id}/bgImgSeq')
        os.makedirs(tempDir,exist_ok=True)
        return tempDir

    def getBgVideoPath(self):
        if self.bgVideoType ==1:
            return ImageApiRes.objects.get(id=self.bgVideoID).image.path
        elif self.bgVideoType ==3:
            return VideoApiRes.objects.get(id=self.bgVideoID).video.path
        elif self.bgVideoType ==2 or self.bgVideoType ==4:
            return FileUpload.objects.get(id=self.bgVideoID).media_file.path
        elif self.bgVideoType ==5:
            if self.isSnapshotMergeTag:
                return os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,settings.VIDEO_SNAPSHOT_DEFAULT_IMAGE_PATH)
            else:
                try:
                    return SnapshotUrl.objects.get(id=self.bgVideoID).image.path
                except:
                    return os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,settings.VIDEO_SNAPSHOT_DEFAULT_IMAGE_PATH)
        elif self.bgVideoType ==6:
            return VideoGradientColor.objects.get(id=self.bgVideoID).media_file.path
        return None

    def getUniqueDataM(self,text):

        data = {
            "id": self.id,"text": text,"videoThemeTemplate": self.videoThemeTemplate.id,"themeTemplateName": self.videoThemeTemplate.name,"videoThemeTemplateData": json.loads(self.videoThemeTemplateData),"bgVideoType": self.bgVideoType,
            "bgVideoID": self.bgVideoID,"bgColor": self.bgColor,"isSnapshotMergeTag": self.isSnapshotMergeTag,"prsCategory": self.prsCategory,"prsPosition": self.prsPosition,
            "prsBgType": self.prsBgType,"prsBgImageId": self.prsBgImageId,"prsBgColor": self.prsBgColor,"isLogo": self.isLogo,"isMusic": self.isMusic
            }

        data['bgUrl'] = self.getBgVideoPath()
        
        if self.prsBgType ==1:
            data['prsBgUrl'] = ImageApiRes.objects.get(id=self.prsBgImageId).image.path
        elif self.prsBgType ==2:
            data['prsBgUrl'] = FileUpload.objects.get(id=self.prsBgImageId).media_file.path
        elif self.prsBgType ==6:
            data['prsBgUrl'] = VideoGradientColor.objects.get(id=self.prsBgImageId).media_file.path

        
        if self.isLogo and self.logo:
            data['logoUrl'] = FileUpload.objects.get(id=self.logo.id).media_file.path
            data['logo'] = self.logo.id
        if self.isMusic != 0:
            if self.music == 1:
                data['music'] = self.music.id
                data['musicUrl'] = FileUpload.objects.get(id=self.music.id).media_file.path
        return data


    def getUniqueData(self,aitaskId = None,aiTaskTotalOutputFrame = None,aiTaskStartFrame = None):
        if self.aitask:
            aitaskId = self.aitask.id
            aiTaskTotalOutputFrame = self.aitask.totalOutputFrame
            aiTaskStartFrame = self.aitask.start_frame

        data = {
            "id": self.id,"aitask": aitaskId,"videoThemeTemplate": self.videoThemeTemplate.id,"themeTemplateName": self.videoThemeTemplate.name,"videoThemeTemplateData": json.loads(self.videoThemeTemplateData),"bgVideoType": self.bgVideoType,
            "bgVideoID": self.bgVideoID,"bgColor": self.bgColor,"isSnapshotMergeTag": self.isSnapshotMergeTag,"prsCategory": self.prsCategory,"prsPosition": self.prsPosition,
            "prsBgType": self.prsBgType,"prsBgImageId": self.prsBgImageId,"prsBgColor": self.prsBgColor,"isLogo": self.isLogo,"isMusic": self.isMusic,"totalAvatarFrames": aiTaskTotalOutputFrame,
            "startFrame": aiTaskStartFrame
            }

        data['bgUrl'] = self.getBgVideoPath()
        
        if self.prsBgType ==1:
            data['prsBgUrl'] = ImageApiRes.objects.get(id=self.prsBgImageId).image.path
        elif self.prsBgType ==2:
            data['prsBgUrl'] = FileUpload.objects.get(id=self.prsBgImageId).media_file.path
        elif self.prsBgType ==6:
            data['prsBgUrl'] = VideoGradientColor.objects.get(id=self.prsBgImageId).media_file.path

        
        if self.isLogo and self.logo:
            data['logoUrl'] = FileUpload.objects.get(id=self.logo.id).media_file.path
            data['logo'] = self.logo.id
        if self.isMusic != 0:
            if self.music == 1:
                data['music'] = self.music.id
                data['musicUrl'] = FileUpload.objects.get(id=self.music.id).media_file.path
        return data

    def getVideoOutputDir(self):
        outDir = f'private_data/singlescene/{self.id}/' #settings.MEDIA_ROOT
        Path(outDir).mkdir(parents=True, exist_ok=True)
        return os.path.join(outDir,'video.mp4')

    def getParsedText(self):
        text =self.text
        allUsedMergeTag = list(set(["{{" + ii + "}}" for ii in re.findall(settings.MERGE_TAG_PATTERN,text)]))
        for _tag in allUsedMergeTag:
            text = text.replace(_tag,_tag[2:-2])
        return text
    
    def getCustomParsedText(self,mergeTags):
        text = self.text
        for name in mergeTags:
            value = mergeTags[name]
            text = text.replace(name,value)
        return text

    class Meta:
        ordering = ['timestamp']


from backgroundclip.models import ImageApiRes, VideoApiRes

@receiver(post_save, sender=VideoRenderSingleScene)
def save_api_data_to_disk(sender, instance, created, **kwargs):

    #if api video then save
    if instance.bgVideoType == 3:
        tmpI = VideoApiRes.objects.get(id=instance.bgVideoID)
        if not tmpI.is_save:
            tmpI.is_save = True
            tmpI.save()
    if instance.bgVideoType == 1:
        tmpI = ImageApiRes.objects.get(id=instance.bgVideoID)
        if not tmpI.is_save:
            tmpI.is_save = True
            tmpI.save()
    if instance.prsBgType == 1:
        tmpI = ImageApiRes.objects.get(id=instance.prsBgImageId)
        if not tmpI.is_save:
            tmpI.is_save = True
            tmpI.save()
            


GENERATE_STATUS = (
    (0,'ERROR'),

    (2,'PENDING'),
    (3,'RUNNING'),

    (1,'COMPLETED'),
)


VIDEO_GENERATE_STATUS = (
    (0,'ERROR'),
    (1,'COMPLETED'),

    (2,'PENDING'),
    (3,'AI_COMPLETED'),
    (4,'RUNNING'),

)


## isDefault === Source => (1=True=Generated From Video Editor,0=False = From Campaign,2=From Video Details)
VIDEO_IS_DEFAULT = (
    ('MAIN_VIDEO',1),
    ('VIDEO_DETAILS',2),
    ('SOLO_CAMPAIGN',3),
    ('GROUP_CAMPAIGN',4),
)

def sendVideoProgressData(data):
    signalData = {"type": "mainVideoProgressUpdate","data": data }
    channel_layer = get_channel_layer()
    user = data.pop('user')
    async_to_sync(channel_layer.group_send)(
        str(user),
        {
            "type": "sendSignals",
            "text": signalData,
        },
    )
    return 0




THUMBNAIL_TYPE= (
    (0,'UPLOAD'),
    (1,'VIDEO_FRAME'), # S(start) M(middle) E(end)
    (2,'{Name}'),# {'part1': "",'part2': ""}
    (3,"{WebsiteScreenshot}")
)



class VideoRenderMultipleScene(models.Model):
    
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    avatar_image = models.ForeignKey(AvatarImages, on_delete=models.CASCADE)
    avatar_sound = models.ForeignKey(AvatarSounds, on_delete=models.CASCADE)

    singleScene = models.ManyToManyField(VideoRenderSingleScene,blank=True)

    sceneThumbnails = models.ManyToManyField('videoThumbnail.MainThumbnail',blank=True,related_name="VideoRenderMultipleScene_sceneThumbnails")
    selectedThumbnail = models.ForeignKey('videoThumbnail.MainThumbnail',blank=True,null=True,on_delete=models.SET_NULL,related_name="VideoRenderMultipleScene_selectedThumbnail")

    thumbnailImage = models.ImageField(upload_to='videom/preview/',default='videom/preview/default.jpg')
    generateStatus = models.OneToOneField('GeneratedFinalVideo', null=True, blank=True,on_delete=models.SET_NULL)

    descriptions = models.CharField(max_length=3000,default='',blank=True,null=True)
    tags = models.CharField(max_length=200,default='',blank=True,null=True)

    userColors = models.CharField(max_length=5000,default='',blank=True,null=True)

    isPublic = models.BooleanField(default=False)
    publicId = models.IntegerField(default=-1)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.name

    def getUsedMergeTag(self,includeThumbnail=True,onlyList=False):
        allMT = []
        for inst in self.singleScene.all():
            allTag = ['{{'+ i+ '}}' for i in re.findall(settings.MERGE_TAG_PATTERN, inst.text)]
            if inst.bgVideoType == 5:
                if inst.isSnapshotMergeTag:
                    allTag.append("{{WebsiteScreenshot}}")
            allMT.extend(allTag)
        if includeThumbnail:
            if self.selectedThumbnail:
                allMT.extend(self.selectedThumbnail.getMergeTag())
        allMT = sorted(set(allMT))
        if onlyList:
            return allMT
        else:
            outputF = []
            for ind,ii in enumerate(allMT):
                outputF.append({"id": ind,"name": ii,"value": ii[2:-2]})
            return outputF
       

    def getAiPosition(self):
        positionX,positionY = (self.avatar_image.faceSwapPositionX,self.avatar_image.faceSwapPositionY)
        scale = self.avatar_image.faceSwapScale
        prvPosX,prvPosY = (-256*scale,-256*scale)
        ix,iy = (round(positionX+prvPosX),round(positionY+prvPosY))
        if iy<0:
            iy = 0
        return (ix,iy)

    def getUniqueDataM(self,texts):
        ix,iy = self.getAiPosition()
        allScData = {'avatar_image': self.avatar_image.id,'avatar_sound': self.avatar_sound.id,'scenes': [],'avatarPosX': ix,'avatarPosY': iy}
        for n,scene in enumerate(self.singleScene.all()):
            allScData['scenes'].append(scene.getUniqueDataM(texts[n]))
        return json.dumps(allScData)

    def getUniqueData(self):
        ix,iy = self.getAiPosition()
        allScData = {'avatar_image': self.avatar_image.id,'avatar_sound': self.avatar_sound.id,'scenes': [],'selectedThumbnail': self.selectedThumbnail.id,'avatarPosX': ix,'avatarPosY': iy}
        for scene in self.singleScene.all():
            allScData['scenes'].append(scene.getUniqueData())
        return json.dumps(allScData)


    def setThumbnail(self):
        if self.selectedThumbnail:
            self.thumbnailImage = self.selectedThumbnail.thumbnailImage
            self.save()
            _genSt = self.generateStatus
            if _genSt:
                _genSt.thumbnailImage = self.selectedThumbnail.thumbnailImage
                _genSt.save()
                

      


#from aiQueueManager.serializers import GenerateFinalVideoSerializer
#from campaign.views import sendGroupCampaignEmail
from subscriptions.models import VideoCreditUsage
from math import ceil
class GeneratedFinalVideo(models.Model):

    name = models.CharField(max_length=250,blank=True,null=True)
    multipleScene = models.ForeignKey('VideoRenderMultipleScene', on_delete=models.CASCADE)


    thumbnailImage = models.ImageField(upload_to='videom/preview/',default='videom/preview/default.jpg')
    video = models.FileField(upload_to="video/finalVideo/",blank=True)

    isDefault = models.IntegerField(default=True)
    
    status = models.IntegerField(default= 2,choices=VIDEO_GENERATE_STATUS)
    priority = models.IntegerField(default=0)

    output = models.TextField(blank=True,null=True)

    groupCampaign = models.ForeignKey('campaign.GroupSingleCampaign',null=True,blank=True,on_delete=models.SET_NULL)
    soloCampaign = models.ForeignKey('campaign.SoloCampaign',null=True,blank=True,on_delete=models.SET_NULL)

    isVideoGenerated = models.IntegerField(default=False)
    isSoundGenerated = models.IntegerField(default=False)

    videoUsedMergeTag = models.CharField(max_length=10000,blank=True,null=True)

    totalFrames = models.IntegerField(default=1)
    completedFrames = models.IntegerField(default=0)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        #unique_together = ('multipleScene', 'output','isDefault','name','videoUsedMergeTag')

    def combineAudioVideo(self):
        if self.isVideoGenerated and self.isSoundGenerated:
            time.sleep(1)
            videoOutputPath = os.path.join(settings.BASE_DIR,f"private_data/finalG/{self.id}/video.mp4")
            audioOutputPath = os.path.join(settings.BASE_DIR,f"private_data/finalG/{self.id}/sound.mp3")
            _finalVP = f'video/finalVideo/{uuid1()}.mp4'
            finalOutputPath = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,_finalVP)
            _command = f"ffmpeg -i {videoOutputPath} -i {audioOutputPath} -c:v copy -c:a aac -y {finalOutputPath}"
            #os.system(_command)
            cmd = subprocess.Popen(_command,cwd=os.path.join(settings.BASE_DIR,f"private_data/finalG/{self.id}/"), stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
            self.video.name = _finalVP
            self.status = 1
            self.save()
            return True
        else:
            return False

    def onVideoComplete(self):

        if self.isDefault==1:
            signalData = {"type": "mainVideoProgressUpdate","data":  {"id": self.multipleScene.id,"status": 1,"completedPercentage": 100,"isDefault": self.isDefault} }
        elif self.isDefault == 2:
            videoDetailsD = {"id": self.id,"name": self.name,'status':1,'timestamp': self.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),'multipleScene': self.multipleScene.id}
            if self.isDefault!=2:
                videoDetailsD['name'] = self.multipleScene.name
                videoDetailsD['id'] = self.multipleScene.id
            if self.status==3 or self.status==4:
                videoDetailsD['status'] = 3
            videoDetailsD['completedPercentage'] = self.getApproxPercentage()
            videoDetailsD['video'] = settings.BASE_URL + self.video.url
            videoDetailsD['thumbnailImage'] = settings.BASE_URL + self.thumbnailImage.url
            signalData = {"type": "mainVideoProgressUpdate","data": videoDetailsD}
        elif self.isDefault == 3:
            signalData = {"type": "mainVideoProgressUpdate","data":  {"id": str(self.soloCampaign.id),"uniqueIdentity": self.soloCampaign.uniqueIdentity,"campaign": f"{self.soloCampaign.campaign.id}", 'campaignLink': self.soloCampaign.getShortUrl(),"status": 1,"completedPercentage": 100,"isDefault": self.isDefault} }
        elif self.isDefault == 4:
            signalData = self.groupCampaign.getOverAllGroup()
        else:
            return 0
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            str(self.multipleScene.user.id),
            {
                "type": "sendSignals",
                "text": signalData,
            },
        )

        if self.isDefault == 1 or self.isDefault == 2:
            vinst = VideoCreditUsage(usedCredit=ceil(self.totalFrames/(settings.VIDEOCREDIT_RATE*60)),user=self.multipleScene.user,usedCreditType=0,name=self.multipleScene.name,info=json.dumps({'gid': [self.id]}))
            vinst.save()
        elif self.isDefault == 3:
            vinst = VideoCreditUsage(usedCredit=ceil(self.totalFrames/(settings.VIDEOCREDIT_RATE*60)),user=self.multipleScene.user,usedCreditType=1,name=self.soloCampaign.campaign.name,info=json.dumps({'gid': [self.id],'type': 'solo','id': str(self.soloCampaign.id)}))
            vinst.save()
        elif self.isDefault == 4:
            self.groupCampaign.sendGroupCampaignEmail()
            # t = Thread(target=sendGroupCampaignEmail,args=(self.groupCampaign,))
            # t.start()
        ## custom video
        if self.isDefault == 2 or self.isDefault == 3 or self.isDefault == 4:
            open('../data.txt','a').write(str(self.multipleScene.id)+'\n')
            if self.multipleScene.id == 452 or self.multipleScene.id == 457:
                _trimName = self.video.path.replace('.mp4',"_trim.mp4")
                _trimCommand = f"ffmpeg -i {self.video.path} -ss 0.5 -i {self.video.path} -c copy -map 1:0 -map 0 -shortest -f nut - | ffmpeg -f nut -i - -map 0 -map -0:0 -c copy -y {_trimName}"
                open('../data.txt','a').write(_trimCommand+'\n')
                cmd = subprocess.Popen(_trimCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
                nextVideoPartPath = "/home/govind/VideoAutomation/src/private_data/manualVideo/finalVideoS1.mp4"
                _combineCommand = f'ffmpeg -i {_trimName} -i {nextVideoPartPath} -filter_complex "[0:v] [0:a] [1:v] [1:a] concat=n=2:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" -y {self.video.path}'
                #os.system(_combineCommand)
                cmd = subprocess.Popen(_combineCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
                open('../data.txt','a').write(_combineCommand+'\n')
            elif self.multipleScene.id == 455:
                _trimName = self.video.path.replace('.mp4',"_trim.mp4")
                _trimCommand = f"ffmpeg -i {self.video.path} -ss 0.5 -i {self.video.path} -c copy -map 1:0 -map 0 -shortest -f nut - | ffmpeg -f nut -i - -map 0 -map -0:0 -c copy -y {_trimName}"
                open('../data.txt','a').write(_trimCommand+'\n')
                cmd = subprocess.Popen(_trimCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
                nextVideoPartPath = "/home/govind/VideoAutomation/src/private_data/manualVideo/dgmFinal.mp4"
                _combineCommand = f'ffmpeg -i {_trimName} -i {nextVideoPartPath} -filter_complex "[0:v] [0:a] [1:v] [1:a] concat=n=2:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" -y {self.video.path}'
                cmd = subprocess.Popen(_combineCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
                open('../data.txt','a').write(_combineCommand+'\n')


    
    def setupTotalFrames(self):
        totalScene = self.multipleScene.singleScene.all()
        uniqueData = json.loads(self.output)
        allScenes = uniqueData['scenes']
        totalAiFrame = 0
        for crntSc,singleScene in enumerate(totalScene):
            queue_inst, created = AiTask.objects.get_or_create(avatar_image=self.multipleScene.avatar_image,avatar_sound=self.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
            if queue_inst.text.strip() == '':
                totalAiFrame+=1
            else:
                isSound = queue_inst.generateSound()
                if isSound:
                    totalAiFrame+=queue_inst.totalOutputFrame
        self.totalFrames = max(1,totalAiFrame)
        self.save()
        data = {"id": self.id,"status": 3,"completedPercentage": 0,"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        if self.isDefault == 1:
            data = {"id": self.multipleScene.id,"status": 3,"completedPercentage": 0,"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        elif self.isDefault == 2:
            data = {"id": self.id,"status": 3,"completedPercentage": 0,"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        elif self.isDefault == 3:
            data = {"id": str(self.soloCampaign.id),"status": 3,"completedPercentage": 0,"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        else:
            return 0
        th = Thread(target=sendVideoProgressData,args=(data,))
        th.start()
        return 0
    
    def getApproxPercentage(self):
        if self.status==0 or self.status==2:
            return 0
        elif self.status==1:
            return 100
        elif self.status==3 or self.status==4:
            return int(min(round(self.completedFrames/self.totalFrames,2),0.98)*100)
        else:
            return 0

    def updateProgress(self,currentProcessingFrame):
        self.completedFrames = currentProcessingFrame
        self.save()
        if self.isDefault == 1:
            data = {"id": self.multipleScene.id,"status": 3,"completedPercentage": self.getApproxPercentage(),"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        elif self.isDefault == 2:
            data = {"id": self.id,"status": 3,"completedPercentage": self.getApproxPercentage(),"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        elif self.isDefault == 3:
            data = {"id": str(self.soloCampaign.id),"status": 3,"completedPercentage": self.getApproxPercentage(),"user": self.multipleScene.user.id,"isDefault": self.isDefault}
        else:
            return 0
        th = Thread(target=sendVideoProgressData,args=(data,))
        th.start()
        return 0
            
    
    def getThumbnailPath(self):
        return os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'videom/preview/')

    def getcwd(self):
        tpath = f"private_data/finalG/{self.id}/"
        os.makedirs(tpath,exist_ok=True)
        return tpath

    def getVideoFileName(self):
        tpath = os.path.join(settings.MEDIA_ROOT,"video/finalVideo/")
        os.makedirs(tpath,exist_ok=True)
        filename = str(uuid1())+".mp4"
        return tpath,filename

    def calculateApproxDuration(self):
        aifps = 0.1 #1/10
        fsfps = 0.1 #1/10
        mvfps = 0.1 #1/10
        totalD = 10
        remaingD = 2
        return (totalD,remaingD)

    def setThumbnail(self,playButton=False):
        ## parse canvas data
        if self.isDefault == 1 or self.isDefault == 2:
            isValid ,canvasData = self.multipleScene.selectedThumbnail.getParseFabricJsonData(json.loads(self.videoUsedMergeTag))
            if isValid:
                outputPath = self.thumbnailImage.path
                uuidName = os.path.basename(outputPath)
                outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                
                fabricData = {"jsonData": canvasData,"outputPath": outputPath,"playButton": playButton}
                ## RABBIT MQ Send Job
                rabbitMQSendJob('fabricJsonToImage',json.dumps(fabricData),durable=True)
                self.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                self.save()
        elif self.isDefault == 3:
            isValid ,canvasData = self.soloCampaign.campaign.selectedThumbnail.getParseFabricJsonData(json.loads(self.soloCampaign.data))
            if isValid:
                outputPath = self.thumbnailImage.path
                uuidName = os.path.basename(outputPath)
                outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                
                fabricData = {"jsonData": canvasData,"outputPath": outputPath,"playButton": playButton}
                ## RABBIT MQ Send Job
                rabbitMQSendJob('fabricJsonToImage',json.dumps(fabricData),durable=True)
                self.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                self.save()
                self.soloCampaign.thumbnail = outputPath.split(settings.MEDIA_ROOT)[1].replace(".jpeg","_play.jpeg")
                self.soloCampaign.save()

        elif self.isDefault == 3:
            isValid ,canvasData = self.groupCampaign.groupcampaign.campaign.selectedThumbnail.getParseFabricJsonData(json.loads(self.videoUsedMergeTag))
            if isValid:
                outputPath = self.thumbnailImage.path
                uuidName = os.path.basename(outputPath)
                outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                
                fabricData = {"jsonData": canvasData,"outputPath": outputPath,"playButton": playButton}
                ## RABBIT MQ Send Job
                rabbitMQSendJob('fabricJsonToImage',json.dumps(fabricData),durable=True)
                self.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                self.save()
                self.groupCampaign.thumbnail = outputPath.split(settings.MEDIA_ROOT)[1].replace(".jpeg","_play.jpeg")
                self.groupCampaign.save()