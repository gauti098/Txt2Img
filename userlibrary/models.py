from email.policy import default
from pyexpat import model
from django.db import models
from django.contrib.auth import get_user_model
import cv2,json,librosa,os,subprocess
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from numpy.core.defchararray import mod
from uuid import uuid4
from django.utils.crypto import get_random_string
from shutil import move,copy
from moviepy.editor import AudioFileClip

from django.conf import settings

from utils.common import executeCommand, getVideoDuration
from PIL import Image



class FileUpload(models.Model):
    # Custom fields
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=250)

    category = models.CharField(default='upload',max_length=20)

    media_type = models.CharField(max_length=250)
    media_file = models.FileField(upload_to='userlibrary/file/')
    original_file = models.FileField(upload_to='userlibrary/file/',blank=True,null=True)
    media_thumbnail = models.ImageField(upload_to='userlibrary/thumbnail/',blank=True)

    aiGeneratedVideo = models.IntegerField(default=0,blank=True,null=True)
    fileInfo = models.CharField(max_length=2500,blank=True,null=True)

    isPublic = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.name}"

    def getMediaExtensions(self):
        return ['video/quicktime','video/avi','video/msvideo','video/x-msvideo','video/x-matroska']

    def getAvatarSpeechCategory(self):
        return ['speechupload','speechrecord']

    def getcwd(self):
        _cwd = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"userlibrary/file/")
        os.makedirs(_cwd,exist_ok=True)
        return _cwd
    
    def getThumbnailDir(self):
        _cwd = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"userlibrary/thumbnail/")
        os.makedirs(_cwd,exist_ok=True)
        return _cwd

    def getModelSoundPath(self):
        return "userlibrary/file/"

    def imageThumbnail(self,previewWidth=640):
        filetype,ext = self.media_type.split('/')
        if filetype == 'image':
            try:
                _image = Image.open(self.media_file.path)
                wpercent = (previewWidth/float(_image.size[0]))
                hsize = int((float(_image.size[1])*float(wpercent)))
                _image.thumbnail((previewWidth,hsize),Image.ANTIALIAS)
                _fileName = f"{uuid4()}.webp"
                _image.save(os.path.join(self.getThumbnailDir(),_fileName),'WEBP')
                self.media_thumbnail.name = f"userlibrary/thumbnail/{_fileName}"
                self.save()
                return True
            except:
                return False
        return 0



    def getFileName(self):
        ext = None
        if self.media_type:
            fileType,ext = self.media_type.split('/')
        _fileName = os.path.basename(self.media_file.path)
        _fileNameE = _fileName.split('.')
        if len(_fileNameE)>1:
            ext = _fileNameE[-1]
        return f"{get_random_string(length=32)}.{ext}"

    def renameFile(self):
        _fileName = self.getFileName()
        _getFilePath = self.media_file.path
        _newFileName = os.path.join(os.path.dirname(_getFilePath),_fileName)
        move(_getFilePath,_newFileName)
        self.media_file = _newFileName.split(settings.MEDIA_ROOT)[1]
        self.save()

    def handleGif(self):
        if self.media_type=='image/gif':
            _filePath = self.media_file.path
            _orgp = self.media_file.name
            _outputPath = os.path.join(os.path.dirname(_filePath),f"{get_random_string(length=32)}.webm")
            copy(_filePath,_outputPath)
            ffmpegPipe = subprocess.Popen(['ffmpeg','-y','-i', _filePath,'-c:v','libvpx-vp9','-qmin', '0','-qmax','25','-crf','9','-b:v','1400K','-quality','good','-auto-alt-ref','0','-pix_fmt', 'yuva420p','-an','-sn',_outputPath ], stdin=subprocess.PIPE, stderr=subprocess.PIPE,shell=False)
            out, err = ffmpegPipe.communicate()
            if out:
                out = out.decode()
            if err:
                err = err.decode()
            self.media_file = _outputPath.split(settings.MEDIA_ROOT)[1]
            self.media_type = 'video/webm'
            self.fileInfo = self.getVideoDuration(_outputPath)
            self.original_file.name = _orgp
            self.save()
            #os.remove(_filePath)
    
    def handleVideo(self,process=0,FPS=30):
        if self.media_type in self.getMediaExtensions() or process:
            _filePath = self.media_file.path
            _orgp = self.media_file.name
            _outputPath = os.path.join(os.path.dirname(_filePath),f"{get_random_string(length=32)}.mp4")
            copy(_filePath,_outputPath)
            _ffmpegCommand = ['ffmpeg','-fflags','+genpts', '-y','-i',_filePath,'-r',f"{FPS}",_outputPath]
            _res = executeCommand(_ffmpegCommand)
    
            self.media_file = _outputPath.split(settings.MEDIA_ROOT)[1]
            self.media_type = 'video/mp4'
            self.fileInfo = self.getVideoDuration(_outputPath)
            self.original_file.name = _orgp
            self.save()
            #os.remove(_filePath)
        else:
            self.setDuration()
            ## handle as mp4
        return True


    def handleVideoOld(self):
        if self.media_type in self.getMediaExtensions():
            _filePath = self.media_file.path
            _orgp = self.media_file.name
            _outputPath = os.path.join(os.path.dirname(_filePath),f"{get_random_string(length=32)}.webm")
            copy(_filePath,_outputPath)
            ffmpegPipe = subprocess.Popen(['ffmpeg','-y','-i', _filePath,'-c:v','libvpx-vp9','-vf',"fps=30",'-qmin', '10','-qmax','42','-quality','good','-cpu-used','0','-b:v','7000k','-maxrate','500k','-bufsize','1500k','-threads','8','-auto-alt-ref','0','-c:a','libvorbis',_outputPath ], stdin=subprocess.PIPE, stderr=subprocess.PIPE,shell=False)
            out, err = ffmpegPipe.communicate()
            if out:
                out = out.decode()
            if err:
                err = err.decode()

            self.media_file = _outputPath.split(settings.MEDIA_ROOT)[1]
            self.media_type = 'video/webm'
            self.fileInfo = self.getVideoDuration(_outputPath)
            self.original_file.name = _orgp
            self.save()
            #os.remove(_filePath)
        else:
            self.setDuration()
            ## handle as mp4
        return True


    def convertAudioToWav(self):
        if self.category in self.getAvatarSpeechCategory():
            if self.original_file:
                return self.original_file.path
            else:
                _loadAudioClip = AudioFileClip(self.media_file.path)
                _fileName = f"{uuid4()}"
                wavOutputPath = os.path.join(self.getcwd(),f"{_fileName}.wav")
                _loadAudioClip.write_audiofile(wavOutputPath,fps = 44100)
                self.original_file.name = self.getModelSoundPath() + f"{_fileName}.wav"
                self.save()
                return wavOutputPath
        return False



    def getVideoDuration(self,_videoPath):
        _data = getVideoDuration(_videoPath)
        return json.dumps(_data)


    def setDuration(self):
        if self.media_type.find('audio')>=0 or self.category in self.getAvatarSpeechCategory():
            try:
                duration = librosa.get_duration(filename=self.media_file.path)
                self.fileInfo = json.dumps({'duration': duration})
                if self.category in self.getAvatarSpeechCategory() and self.media_type == 'video/mp4':

                    self.media_type = 'audio/mp4'
                self.save()
            except:
                pass
        elif self.media_type.find('video')>=0:
            try:
                self.fileInfo = self.getVideoDuration(self.media_file.path)
                self.save()
            except:
                pass
        



