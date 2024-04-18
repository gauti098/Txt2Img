from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
import requests,os,tempfile,uuid
import subprocess
from django.contrib.auth import get_user_model
from django.dispatch import receiver
#from userlibrary.models import FileUpload

from utils.common import download_file, executeCommand, getImageInfo, getVideoDuration, getWebmCodecName
from uuid import uuid4
import json
from shutil import rmtree,copy
from PIL import Image

SAVE_IMAGE_MODEL_TYPE = (
    (0,"APIImageQuerySaver"),
    (1,"APIImagePopularSaver"),
    (2,"FileUpload"),
    (3,"VideoGradientColor"),
)

class APISaveImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(get_user_model(),on_delete=models.SET_NULL,blank=True,null=True)
    name = models.CharField(max_length=100,blank=True,null=True)
    apiVideoInstId = models.IntegerField(blank=True,null=True)
    apiVideoInstType = models.IntegerField(default=2,choices=SAVE_IMAGE_MODEL_TYPE)
    
    previewImage = models.ImageField(upload_to='apiImage/preview/',blank=True,null=True)
    image = models.ImageField(upload_to='apiImage/original/',blank=True,null=True)

    fileInfo = models.CharField(max_length=500,blank=True,null=True)
    originalImageInfo = models.CharField(max_length=500,blank=True,null=True)

    isProcessed = models.BooleanField(default=False)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"apiImage/")
        os.makedirs(_path,exist_ok=True)
        return _path

    def getImagePath(self):
        _path = os.path.join(self.getCwd(),f"original/")
        os.makedirs(_path,exist_ok=True)
        _filePath = os.path.join(_path,f"{self.id}.webp")
        return _filePath
    
    def getImageName(self):
        return f"apiImage/original/{self.id}.webp"

    def getPreviewImagePath(self):
        _path = os.path.join(self.getCwd(),f"preview/")
        os.makedirs(_path,exist_ok=True)
        _filePath = os.path.join(_path,f"{self.id}.webp")
        return _filePath
    
    def getPreviewImageName(self):
        return f"apiImage/preview/{self.id}.webp"

    def convertImage(self,previewWidth=1080,originalWidth=1920):
        try:
            _image = Image.open(self.getImagePath())
            #convert original
            wpercent = (originalWidth/float(_image.size[0]))
            hsize = int((float(_image.size[1])*float(wpercent)))
            _orgImage = _image.resize((originalWidth,hsize), Image.ANTIALIAS)
            _orgImage.save(self.getImagePath(),'WEBP')
            self.originalImageInfo = json.dumps({"width": _orgImage.size[0],"height": _orgImage.size[1]})
            self.image.name = self.getImageName()
            self.save()
            # convert preview
            wpercent = (previewWidth/float(_image.size[0]))
            hsize = int((float(_image.size[1])*float(wpercent)))
            _image.thumbnail((previewWidth,hsize),Image.ANTIALIAS)
            _image.save(self.getPreviewImagePath(),'WEBP')
            self.fileInfo = json.dumps({"width": _image.size[0],"height": _image.size[1]})
            self.previewImage.name = self.getPreviewImageName()
            self.isProcessed = True
            self.save()
            return True
        except:
            copy(self.getImagePath(),self.getPreviewImagePath())
            self.previewImage.name = self.getPreviewImageName()
            self.save()
            return False

@receiver(models.signals.post_delete, sender=APISaveImage)
def auto_delete_file_APISaveImage(sender, instance, **kwargs):
    if instance.previewImage:
        if os.path.isfile(instance.previewImage.path):
            os.remove(instance.previewImage.path)
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
    

SAVE_MODEL_TYPE = (
    (0,"APIVideoQuerySaver"),
    (1,"APIVideoPopularSaver"),
    (2,"FileUpload"),
)


class APISaveVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(get_user_model(),on_delete=models.SET_NULL,blank=True,null=True)
    name = models.CharField(max_length=100,blank=True,null=True)
    apiVideoInstId = models.IntegerField(blank=True,null=True)
    apiVideoInstType = models.IntegerField(default=2,choices=SAVE_MODEL_TYPE)
    srcUrl = models.CharField(max_length=250,blank=True,null=True)


    tags = models.CharField(max_length=500,blank=True,null=True)
    previewThumbnail = models.ImageField(upload_to='apiVideo/preview/thumbnail/',blank=True,null=True)
    thumbnail = models.ImageField(upload_to='apiVideo/original/thumbnail/',blank=True,null=True)

    fileInfo = models.CharField(max_length=500,blank=True,null=True)
    previewVideo = models.FileField(upload_to="apiVideo/preview/video/",blank=True,null=True)
    originalVideo = models.FileField(upload_to="apiVideo/original/video/",blank=True,null=True)
    originalVideoFileInfo = models.CharField(max_length=500,blank=True,null=True)

    isTransparent = models.BooleanField(default=False)
    
    isAudio = models.BooleanField(default=False)
    audio = models.FileField(upload_to='apiVideo/original/audio/',blank=True,null=True)

    isVideoConvertedPreview = models.BooleanField(default=False)
    isVideoProcessed= models.BooleanField(default=False)
    totalFrames = models.IntegerField(default=0)
    isPublic = models.BooleanField(default=True)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.name}"


    def getCwd(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"apiVideo/original/")
        os.makedirs(_path,exist_ok=True)
        return _path

    def getVideoPath(self):
        _path = os.path.join(self.getCwd(),f"video/")
        os.makedirs(_path,exist_ok=True)
        ext = "mp4"
        if self.isTransparent:
            ext = "webm"
        _filePath = os.path.join(_path,f"{self.id}.{ext}")
        return _filePath

    def getPreviewVideoPath(self):
        _path = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,f"apiVideo/preview/video/")
        os.makedirs(_path,exist_ok=True)
        ext = "mp4"
        if self.isTransparent:
            ext = "webm"
        _filePath = os.path.join(_path,f"{self.id}.{ext}")
        return _filePath

    def getThumbnailPath(self):
        _path = os.path.join(self.getCwd(),f"thumbnail/")
        os.makedirs(_path,exist_ok=True)
        ext = 'jpeg'
        if self.isTransparent:
            ext = 'webp'
        _filePath = os.path.join(_path,f"{self.id}.{ext}")
        return _filePath

    def getImageSeqencePath(self,onlyDir=False):
        _path = os.path.join(self.getCwd(),f"imageSequence/{self.id}")
        os.makedirs(_path,exist_ok=True)
        if onlyDir:
            return _path
        else:
            if self.isTransparent:
                _path = os.path.join(_path,"%05d.webp")
            else:
                _path = os.path.join(_path,"%05d.jpeg")
            return _path

    def emptyImageSeq(self):
        _imgSeqDir = self.getImageSeqencePath(onlyDir=True)
        if os.path.exists(_imgSeqDir) and os.path.isdir(_imgSeqDir):
            rmtree(_imgSeqDir)
        return True

    def getVideoName(self):
        ext = "mp4"
        if self.isTransparent:
            ext = "webm"
        return f"apiVideo/original/video/{self.id}.{ext}"

    def getThumbnailName(self):
        ext = 'jpeg'
        if self.isTransparent:
            ext = 'webp'
        return f"apiVideo/original/thumbnail/{self.id}.{ext}"

    def getPreviewVideoName(self):
        ext = "mp4"
        if self.isTransparent:
            ext = "webm"
        return f"apiVideo/preview/video/{self.id}.{ext}"

    def getOriginalVideoInfo(self):
        if self.originalVideo:
            _defVideoInfo = {"duration": 0, "fps": 30, "frame": 0, "height": 1080, "width": 1920}
            if self.originalVideoFileInfo:
                try:
                    _getVideoInfo = json.loads(self.originalVideoFileInfo)
                    _w = _getVideoInfo["width"]
                    return (True,_getVideoInfo)
                except:
                    try:
                        _getVideoInfo = getVideoDuration(self.originalVideo.path)
                        self.originalVideoFileInfo = json.dumps(_getVideoInfo)
                        self.save()
                        _w = _getVideoInfo["width"]
                        return (True,_getVideoInfo)
                    except:
                        return (True,_defVideoInfo)
            else:
                try:
                    _getVideoInfo = getVideoDuration(self.originalVideo.path)
                    self.originalVideoFileInfo = json.dumps(_getVideoInfo)
                    self.save()
                    _w = _getVideoInfo["width"]
                    return (True,_getVideoInfo)
                except:
                    return (True,_defVideoInfo)
        else:
            return (False,None)

    def extractFrames(self,maxWidth=1920,maxHeight=1920,quality=3,fps=settings.VIDEO_DEFAULT_FPS):
        _isSuccess,_videoInfo = self.getOriginalVideoInfo()
        if self.originalVideo and self.isVideoProcessed==False and _isSuccess:
            self.emptyImageSeq()
            _videoHeight = _videoInfo["height"]
            _videoWidth = _videoInfo["width"]

            _ffmpegCommand = None
            _ffmpegCommandT = None
            if self.isTransparent:
                _crntCodecName = getWebmCodecName(self.originalVideo.path)
                if _videoWidth>=_videoHeight:
                    ## horizontal video
                    if _videoWidth>maxWidth:
                        _ffmpegCommandT = ['ffmpeg','-y','-c:v',_crntCodecName,'-i', self.originalVideo.path,'-vf',f'fps={fps},scale={maxWidth}:-2','-c:v', 'libwebp','-start_number','0',self.getImageSeqencePath()]
                    else:
                        _ffmpegCommandT = ['ffmpeg','-y','-c:v',_crntCodecName,'-i', self.originalVideo.path,'-vf',f'fps={fps}','-c:v', 'libwebp','-start_number','0',self.getImageSeqencePath()]
                else:
                    if _videoHeight>maxHeight:
                        _ffmpegCommandT = ['ffmpeg','-y','-c:v',_crntCodecName,'-i', self.originalVideo.path,'-vf',f'fps={fps},scale=-2:{maxHeight}','-c:v', 'libwebp','-start_number','0',self.getImageSeqencePath()]
                    else:
                        _ffmpegCommandT = ['ffmpeg','-y','-c:v',_crntCodecName,'-i', self.originalVideo.path,'-vf',f'fps={fps}','-c:v', 'libwebp','-start_number','0',self.getImageSeqencePath()]

                _res = executeCommand(_ffmpegCommandT)
            else:
                if _videoWidth>=_videoHeight:
                    ## horizontal video
                    if _videoWidth>maxWidth:
                        _ffmpegCommand = ['ffmpeg','-y','-i', self.originalVideo.path,'-vf',f'fps={fps},scale={maxWidth}:-2','-qscale:v',f'{quality}','-start_number','0',self.getImageSeqencePath()]
                    else:
                        _ffmpegCommand = ['ffmpeg','-y','-i', self.originalVideo.path,'-vf',f'fps={fps}','-qscale:v',f'{quality}','-start_number','0',self.getImageSeqencePath()]
                else:
                    if _videoHeight>maxHeight:
                        _ffmpegCommand = ['ffmpeg','-y','-i', self.originalVideo.path,'-vf',f'fps={fps},scale=-2:{maxHeight}','-qscale:v',f'{quality}','-start_number','0',self.getImageSeqencePath()]
                    else:
                        _ffmpegCommand = ['ffmpeg','-y','-i', self.originalVideo.path,'-vf',f'fps={fps}','-qscale:v',f'{quality}','-start_number','0',self.getImageSeqencePath()]

                _res = executeCommand(_ffmpegCommand)

            self.isVideoProcessed = True
            _imgSP = self.getImageSeqencePath(onlyDir=True)
            _allF = os.listdir(_imgSP)
            self.totalFrames = len(_allF)
            _videoInfo["eImgInfo"] = getImageInfo(os.path.join(_imgSP,_allF[0]))
            self.originalVideoFileInfo = json.dumps(_videoInfo)
            self.save()
            return True

    def convertPreview(self,isFileUpload=False,maxWidth=850,quality=25):
        if self.isTransparent==False:
            _ffmpegCommand = None
            if isFileUpload:
                _ffmpegCommand = ['ffmpeg','-y','-i', self.originalVideo.path,'-vf',f'scale={maxWidth}:-2','-crf',f'{quality}',self.getPreviewVideoPath()]
            else:
                _ffmpegCommand = ['ffmpeg','-y','-i', self.originalVideo.path,'-vf',f'scale={maxWidth}:-2','-crf',f'{quality}','-an',self.getPreviewVideoPath()]
            _res = executeCommand(_ffmpegCommand)

            self.fileInfo = json.dumps(getVideoDuration(self.getPreviewVideoPath()))
            self.previewVideo.name = self.getPreviewVideoName()
            self.isVideoConvertedPreview = True
            self.save()
        else:
            #copy(self.originalVideo.path,self.getPreviewVideoPath())
            _crntCodecName = getWebmCodecName(self.originalVideo.path)
            _res = executeCommand(['ffmpeg','-y','-c:v',_crntCodecName,'-i', self.originalVideo.path,'-vf',f'scale={maxWidth}:-2','-auto-alt-ref','0','-c:v','libvpx-vp9',self.getPreviewVideoPath()])
            _res = executeCommand(['ffmpeg','-y','-c:v',_crntCodecName,'-i', self.originalVideo.path,'-frames:v','1','-c:v', 'libwebp',self.getThumbnailPath()])
                
            self.fileInfo = json.dumps(getVideoDuration(self.getPreviewVideoPath()))
            self.previewVideo.name = self.getPreviewVideoName()
            self.isVideoConvertedPreview = True
            self.save()


    


@receiver(models.signals.post_delete, sender=APISaveVideo)
def auto_delete_file_APISaveVideo(sender, instance, **kwargs):
    if instance.previewThumbnail:
        if os.path.isfile(instance.previewThumbnail.path):
            os.remove(instance.previewThumbnail.path)
    if instance.thumbnail:
        if os.path.isfile(instance.thumbnail.path):
            os.remove(instance.thumbnail.path)
    if instance.previewVideo:
        if os.path.isfile(instance.previewVideo.path):
            os.remove(instance.previewVideo.path)
    if instance.originalVideo:
        if os.path.isfile(instance.originalVideo.path):
            os.remove(instance.originalVideo.path)
    instance.emptyImageSeq()




class VideoSearch(models.Model):
    query_string = models.CharField(max_length=50)
    provider_page = models.IntegerField(default=1)
    provider_name = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now=False,auto_now_add=True)
    
    def __str__(self):
        return f"{self.query_string}_{self.provider_name}_{self.provider_page}"


class APIVideoQuerySaver(models.Model):

    _queryString = models.CharField(max_length=500)
    _order = models.IntegerField(default=0)
    _page = models.IntegerField(default=0)
    _apiProvider = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    low_url = models.URLField(max_length=500)
    high_url = models.URLField(max_length=500)
    thumbnail = models.CharField(max_length=500,default='')
    fileInfo = models.CharField(max_length=500,blank=True,null=True)
    data = models.CharField(max_length=1000,blank=True,null=True)
    
    timestamp = models.DateTimeField(auto_now=False,auto_now_add=True)

    class Meta:
        ordering = ['_order']

    def __str__(self):
        return self.name

    def getThumbnailUrlAndTags(self):
        _data = json.loads(self.data)
        return (_data.get("thumbnail",self.thumbnail),_data.get("tags",""))


class APIVideoPopularSaver(models.Model):

    name = models.CharField(max_length=500)
    source = models.CharField(max_length=50,blank=True,null=True)
    low_url = models.URLField(max_length=500)
    high_url = models.URLField(max_length=500)
    thumbnail = models.CharField(max_length=500,default='')
    fileInfo = models.CharField(max_length=500,blank=True,null=True)
    data = models.CharField(max_length=1000,blank=True,null=True)

    timestamp = models.DateTimeField(auto_now=False,auto_now_add=True)

    def __str__(self):
        return self.name

    def getThumbnailUrlAndTags(self):
        _data = json.loads(self.data)
        return (_data.get("thumbnail",self.thumbnail),_data.get("tags",""))




class VideoApiRes(models.Model):

    query = models.ForeignKey(VideoSearch, on_delete=models.SET_NULL,null=True )
    name = models.CharField(max_length=200)
    low_url = models.URLField(max_length=200)
    high_url = models.URLField(max_length=200)
    thumbnail = models.CharField(max_length=250,default='')
    fileInfo = models.CharField(max_length=500,blank=True,null=True)
    data = models.CharField(max_length=1000,blank=True,null=True)
    is_save = models.BooleanField(default=False)

    video = models.FileField(upload_to="api_videos/", blank=True)
    
    updated = models.DateTimeField(auto_now=True,auto_now_add=False)

    def __str__(self):
        return self.name


@receiver(post_save, sender=VideoApiRes, dispatch_uid="save_api_video")
def save_api_video(sender, instance, **kwargs):
    cache_dir = '/tmp/_cache/'
    os.makedirs(cache_dir,exist_ok=True)
    if instance.is_save and bool(instance.video) is False:
        file_name = f"{instance.id}_{uuid.uuid4()}"

        os.makedirs(cache_dir,exist_ok=True)
        finalFN = os.path.join(cache_dir,file_name)
        download_file(instance.high_url,finalFN)
        
        _command1 = f'ffmpeg -y -i "{finalFN}" -c copy -f h264 "{finalFN}.h264"'
        _command2 = f'ffmpeg -y -r {settings.VIDEO_DEFAULT_FPS} -i "{finalFN}.h264" -c copy "{finalFN}.mp4"'
        cmd = subprocess.Popen(_command1,cwd=cache_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
        cmd = subprocess.Popen(_command2,cwd=cache_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
        #os.system(f'ffmpeg -y -i "{cache_dir+file_name}" -c copy -f h264 "{cache_dir+file_name}.h264"')
        #os.system(f'ffmpeg -y -r {settings.VIDEO_DEFAULT_FPS} -i "{cache_dir+file_name}.h264" -c copy "{cache_dir+file_name}.mp4"')
        crntv = open(f"{finalFN}.mp4",'rb')
        instance.video.save(f"{file_name}.mp4", File(crntv))
        crntv.close()
        os.remove(finalFN)
        os.remove(f"{finalFN}.h264")
        os.remove(f"{finalFN}.mp4")
        

class ImageSearch(models.Model):
    query_string = models.CharField(max_length=50)
    provider_name = models.CharField(max_length=50)
    provider_page = models.IntegerField(default=1)
    timestamp   = models.DateTimeField(auto_now=False,auto_now_add=True)
    
    def __str__(self):
        return f"{self.query_string}_{self.provider_name}_{self.provider_page}"


API_MEDIA_TYPE = (
    (0,'Image'),
    (1,'Video')
)

API_MEDIA_STATE = (
    (0,'Error'),
    (1,'Running'),
    (2,'Completed'),
    (3,'Pending'),

)

class ApiQueryLogger(models.Model):
    query = models.CharField(max_length=500)
    providerName = models.CharField(max_length=50)
    page = models.IntegerField(default=1)
    _type = models.IntegerField(default=0,choices=API_MEDIA_TYPE)
    state = models.IntegerField(default=3,choices=API_MEDIA_STATE)
    timestamp   = models.DateTimeField(auto_now=False,auto_now_add=True)
    


class APIImageQuerySaver(models.Model):

    _queryString = models.CharField(max_length=500)
    _order = models.IntegerField(default=0)
    _page = models.IntegerField(default=0)
    _apiProvider = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    low_url = models.URLField(max_length=500)
    high_url = models.URLField(max_length=500)
    data = models.CharField(max_length=1000,blank=True,null=True)
    
    timestamp = models.DateTimeField(auto_now=False,auto_now_add=True)

    class Meta:
        ordering = ['_order']

    def __str__(self):
        return self.name


class APIImagePopularSaver(models.Model):

    name = models.CharField(max_length=500)
    source = models.CharField(max_length=50,blank=True,null=True)
    low_url = models.URLField(max_length=500)
    high_url = models.URLField(max_length=500)
    data = models.CharField(max_length=1000,blank=True,null=True)

    timestamp = models.DateTimeField(auto_now=False,auto_now_add=True)

    def __str__(self):
        return self.name




class ImageApiRes(models.Model):

    query = models.ForeignKey(ImageSearch, on_delete=models.SET_NULL,null=True)
    name = models.CharField(max_length=200)
    low_url = models.URLField(max_length=200)
    high_url = models.URLField(max_length=200)

    is_save = models.BooleanField(default=False)
    image = models.ImageField(upload_to="api_images/", blank=True)
    
    updated = models.DateTimeField(auto_now=True,auto_now_add=False)
    

    def __str__(self):
        return self.name

@receiver(post_save, sender=ImageApiRes, dispatch_uid="save_api_images")
def save_api_images(sender, instance, **kwargs):
    if instance.is_save and bool(instance.image) is False:
        file_name = f"{uuid.uuid4()}.png"
        temp = tempfile.NamedTemporaryFile(delete = True)
        temp.write(requests.get(instance.high_url).content)
        temp.flush()
        instance.image.save(f"{instance.id}_{file_name}", File(temp))