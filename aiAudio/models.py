import logging
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
import os,json
import librosa
import traceback
from uuid import uuid4
from threading import Thread

from aiAudio.utils.loadAudioFile import convertMp3AudioToWav, pydubCombineAudioFile, pydubLoadFile,pydubBlankAudio
from aiAudio import task as aiAudioTask

logger = logging.getLogger(__name__)

class AiAudio(models.Model):

    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL,blank=True,null=True)
    avatarSound = models.ForeignKey('appAssets.AvatarSounds', on_delete=models.CASCADE)
    text = models.CharField(max_length=5000)
    sound = models.FileField(upload_to='usersound/generated/',blank=True,null=True)
    isGenerated = models.BooleanField(default=False)
    soundDuration = models.FloatField(default=0)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.avatarSound.name}_{self.text[:50]}....."

    def getcwd(self):
        _cwd = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"usersound/generated/")
        os.makedirs(_cwd,exist_ok=True)
        return _cwd
    
    def getModelSoundPath(self):
        return "usersound/generated/"

    def setAudioDuration(self):
        if self.isGenerated:
            try:
                _audioPath = self.sound.path
                self.soundDuration = librosa.get_duration(filename=_audioPath)
                self.save()
                return True
            except:
                logger.error(f"Unable to Get Audio Duration: {str(traceback.format_exc())}")
                return False
        else:
            return 0

    def aiGenerateSound(self,TOTAL_TRIES = 3):
        if self.isGenerated and self.sound:
            return True
        if self.text.strip() == '':
            _soundname = f"{uuid4()}.mp3"
            audioPath = os.path.join(self.getcwd(),_soundname)
            _pyDub = pydubBlankAudio(1)
            _pyDub.export(audioPath, parameters=["-ar","44100","-ac", "2","-q:a", "0"])
            self.soundDuration = 1
            self.sound.name = self.getModelSoundPath() + _soundname
            self.isGenerated = True
            self.save()
            return True
        for _ in range(TOTAL_TRIES):
            outputPath = self.getcwd()
            _soundname = f"{uuid4()}.mp3"
            audioPath = os.path.join(outputPath,_soundname)
            isSuccess,message = self.avatarSound.generateSound(self.text,audioPath)
            if isSuccess:
                self.sound.name = self.getModelSoundPath() + _soundname
                self.isGenerated = True
                self.save()
                self.setAudioDuration()
                return True
        return False


def saveAudioClip(inputPath,outputPath):
    _pydubI =pydubLoadFile(inputPath)
    _pydubI.export(outputPath)
    return True

class AiCombineAudio(models.Model):

    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL,blank=True,null=True)
    allAudioInfo = models.CharField(max_length=5000)
    sound = models.FileField(upload_to='usersound/combine_generated/',blank=True,null=True)
    wav_sound = models.FileField(upload_to='usersound/combine_generated/',blank=True,null=True)
    isGenerated = models.BooleanField(default=False)
    soundDuration = models.FloatField(default=0)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

   

    def getcwd(self):
        _cwd = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,"usersound/combine_generated/")
        os.makedirs(_cwd,exist_ok=True)
        return _cwd

    def getModelSoundPath(self):
        return "usersound/combine_generated/"

    def combineMultipleAiAudio(self,allInst,allAudioInfo=None,isWavThread=True,startDelay=0.7,minimumDuration=6):
        try:
            if allAudioInfo==None:
                allAudioInfo = json.loads(self.allAudioInfo)
            finalAudioConcat = []
            audioCombine = []
            _finalAudioDuration = 0
            for n,inst in enumerate(allInst):
                _delay = allAudioInfo[n]['delay']
                if n==0:
                    if _delay<startDelay:
                        _delay = startDelay
                if _delay>0:
                    audioCombine.append({'type': 'blank','duration': _delay})
                    _finalAudioDuration += _delay
                if inst.sound:
                    audioCombine.append({'type': 'file','path': inst.sound.path})
                    _duration = inst.soundDuration
                    _finalAudioDuration += _duration

            if _finalAudioDuration<minimumDuration:
                _lastDelay = minimumDuration - _finalAudioDuration
                if _lastDelay<startDelay:
                    _lastDelay = startDelay
                _finalAudioDuration += _lastDelay
                audioCombine.append({'type': 'blank','duration': _lastDelay})
            else:
                _finalAudioDuration += startDelay
                audioCombine.append({'type': 'blank','duration': startDelay})
            _fileName = f"{uuid4()}"
            _saveFN = os.path.join(self.getcwd(),f"{_fileName}.mp3")
            pydubCombineAudioFile(audioCombine,_saveFN)
            
            wavOutputPath = os.path.join(self.getcwd(),f"{_fileName}.wav")
            if isWavThread:
                aiAudioTask.convertMp3AudioToWav.delay({"inputPath": _saveFN,"outputPath": wavOutputPath})
            else:
                convertMp3AudioToWav({"inputPath": _saveFN,"outputPath": wavOutputPath})
            
            self.sound.name = self.getModelSoundPath() + f"{_fileName}.mp3"
            self.wav_sound.name = self.getModelSoundPath() + f"{_fileName}.wav"
            self.soundDuration = round(_finalAudioDuration,2)
            self.isGenerated = True
            self.save()
            return True
        except Exception as e:
            logger.error(f"Unable to Combine Audio With delay Exception: {e} Stack: {str(traceback.format_exc())}")
            return False
            
        
  
        
        