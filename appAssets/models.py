from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from google.cloud import texttospeech
from externalApi.wellsaid import wellSaidApi
from externalApi.microsoftTTS import microsoftApi
import json,os

import numpy as np
from skimage.transform import resize
import cv2, os
import json
from tqdm import tqdm
from glob import glob


GENDER_CHOICES = (
    (1, ("Male")),
    (2, ("Female")),
)

class AvatarImages(models.Model):

    name = models.CharField(max_length=50)
    gender = models.IntegerField(choices=GENDER_CHOICES, default=1)  
    img = models.ImageField(upload_to='avatars/image/',blank=True,null=True)
    largeImg = models.ImageField(upload_to='avatars/image/',blank=True,null=True)
    transparentImage = models.ImageField(upload_to='avatars/image/',blank=True,null=True)
    avatarConfig = models.CharField(max_length=10000,blank=True,null=True)
    #img_high = models.ImageField(upload_to='avatars/low/')

    faceSwapPositionX = models.IntegerField(default=0)
    faceSwapPositionY = models.IntegerField(default=0)
    faceSwapAnchorPointX = models.IntegerField(default=0)
    faceSwapAnchorPointY = models.IntegerField(default=0)
    faceSwapScale = models.FloatField(default=0)
    totalFrames = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)


    timestamp   = models.DateTimeField(auto_now=False,auto_now_add=True)
    updated = models.DateTimeField(auto_now=True,auto_now_add=False)
    
    def __str__(self):
        return f"{self.name}"

    def getAiPosition(self):
        positionX,positionY = (self.faceSwapPositionX,self.faceSwapPositionY)
        scale = self.faceSwapScale
        newSize = 512*scale
        prvPosX,prvPosY = (-256*scale,-256*scale)

        ix,iy = (positionX+prvPosX,positionY+prvPosY)
        ixf,iyf = round(ix+newSize),round(iy+newSize)
        ix,iy = round(ix),round(iy)
        if iy<0:
            iy = 0
        return (ix,iy,ixf,iyf)
        

    def getMaskPath(self):
        return os.path.join(self.getcwd(),'fullbody/mask.mp4')

    def getImageSeqPath(self):
        return os.path.join(self.getcwd(),'fullbody/imageSequence/')

    def getcwd(self):
        return os.path.join(settings.BASE_DIR,f'private_data/avatars/{self.id}/')
    
    def getWav2lipVideo(self):
        return os.path.join(self.getcwd(),"wav2lip/video.mp4")

    def getSourceFrame(self):
        initImage = os.path.join(self.getcwd(),"first_order/source.npy")
        if os.path.isfile(initImage):
            return initImage
        else:
            tempArr = np.array([resize(cv2.cvtColor(cv2.imread(os.path.join(self.getcwd(),"first_order/source.png")),cv2.COLOR_BGR2RGB), (512, 512))[..., :3]]).astype(np.float32)
            np.save(open(initImage,'wb'),tempArr)
            return initImage


    def getFirstInitFrame(self):
        initImage = os.path.join(self.getcwd(),"first_order/init_frame.npy")
        if os.path.isfile(initImage):
            return initImage
        else:
            tempArr = np.array([resize(cv2.cvtColor(cv2.imread(os.path.join(self.getcwd(),"first_order/init_frame.png")),cv2.COLOR_BGR2RGB), (512, 512))[..., :3]]).astype(np.float32)
            np.save(open(initImage,'wb'),tempArr)
            return initImage

    def getFaceCordinate(self):
        from AiHandler.wav2lip import face_detection
        if os.path.isfile(os.path.join(self.getcwd(),"wav2lip/face_coordinate.npy")):
            return os.path.join(self.getcwd(),"wav2lip/face_coordinate.npy")
        else:
            detector = face_detection.FaceAlignment(face_detection.LandmarksType._2D, flip_input=False, device=settings.DEVICE)
            batch_size = 4
            video_stream = cv2.VideoCapture(os.path.join(self.getcwd(),"wav2lip/video.mp4"))
            images = []
            #crnt_f = 0
            while 1:
                still_reading, frame = video_stream.read()
                if not still_reading:
                    video_stream.release()
                    break
                #cv2.imwrite(os.path.join(self.getcwd(),f"wav2lip/images/{crnt_f}.jpeg"),frame)
                #crnt_f+=1
                images.append(frame)
            predictions = []
            while True:
                try:
                    for i in tqdm(range(0, len(images), batch_size)):
                        predictions.extend(detector.get_detections_for_batch(np.array(images[i:i + batch_size])))
                except RuntimeError:
                    if batch_size == 1: 
                        raise RuntimeError('Image too big to run face detection on GPU.')
                    batch_size //= 2
                    print('Recovering from OOM error; New batch size: {}'.format(batch_size))
                    continue
                break

            results = []
            padding_bottom = 20
            for rect in predictions:
                y1 = rect[1]
                y2 = rect[3] + padding_bottom
                x1 = rect[0]
                x2 = rect[2]
                results.append([x1, y1, x2, y2])

            boxes = np.array(results)
            T=5
            for i in range(len(boxes)):
                if i + T > len(boxes):
                    window = boxes[len(boxes) - T:]
                else:
                    window = boxes[i : i + T]
                boxes[i] = np.mean(window, axis=0)
            
            np.save(open(os.path.join(self.getcwd(),"wav2lip/face_coordinate.npy"), 'wb'),boxes)
        return os.path.join(self.getcwd(),"wav2lip/face_coordinate.npy")

@receiver(post_save, sender=AvatarImages, dispatch_uid="create_data_folder")
def create_data_folder(sender, instance, **kwargs):
    #create avatar root dir
    os.makedirs(f'private_data/avatars/{instance.id}/',exist_ok=True)
    os.makedirs(f'private_data/avatars/{instance.id}/wav2lip/',exist_ok=True)
    os.makedirs(f'private_data/avatars/{instance.id}/first_order/',exist_ok=True)
    os.makedirs(f'private_data/avatars/{instance.id}/fullbody/',exist_ok=True)
    os.makedirs(f'private_data/avatars/{instance.id}/fullbody/mask/',exist_ok=True)
    os.makedirs(f'private_data/avatars/{instance.id}/fullbody/without_swap/',exist_ok=True)


#provider_id for google
'''
{
    "name": "en-IN-Wavenet-A",
    "pitch": 0,
    "language_code": "en-US" 
}
'''

class AvatarSounds(models.Model):

    name = models.CharField(max_length=50)
    voice_language = models.ForeignKey("VoiceLanguage",blank=True,null=True,on_delete=models.SET_NULL)
    gender = models.IntegerField(choices=GENDER_CHOICES, default=1)

    provider = models.CharField(max_length=50)
    provider_id = models.CharField(max_length=200)

    samples = models.FileField(upload_to='appAssets/avatar_sounds/',blank=True,null=True,default="appAssets/avatar_sounds/default.mp3")

    timestamp   = models.DateTimeField(auto_now=False,auto_now_add=True)
    updated = models.DateTimeField(auto_now=True,auto_now_add=False)
    
    def __str__(self):
        return f"{self.name}"

    def generateSound(self,text,output):
        text = text.replace('{','').replace('}','')
        if self.provider == 'google':
            try:
                config = json.loads(self.provider_id)
                if self.gender == 2:
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
                else:
                    ssml_gender = texttospeech.SsmlVoiceGender.MALE

                voice = texttospeech.VoiceSelectionParams(
                    language_code=config['language_code'],
                    name=config['name'],
                    ssml_gender=ssml_gender,
                )

                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3, #LINEAR16
                    pitch=config['pitch']
                )

                response = settings.GOOGLE_TTS_CLIENT.synthesize_speech(
                    input=texttospeech.SynthesisInput(ssml=text), voice=voice, audio_config=audio_config
                )

                with open(output, "wb") as f:
                    f.write(response.audio_content)
                return True,''

            except Exception as e:
                #settings.LOG.error('Error in Generating Google Sound: ' + str(e))
                return False,str(e)

        elif self.provider == 'wellsaid':
            try:
                config = json.loads(self.provider_id)
                _res = wellSaidApi.generateSound(text,config,output)
                return _res,''
            except Exception as e:
                return False,f"{e}"

        elif self.provider == 'microsoft':
            try:
                _res = microsoftApi.generateSound(text,self.provider_id,output)
                return _res,''
            except Exception as e:
                return False,f"{e}"
            
        return False,'Provider is Not Valid.'





class CountryDetails(models.Model):

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)
    image = models.ImageField(upload_to='country/',blank=True,null=True)

    def __str__(self):
        return self.name

    def addFromJson(jsonData):
        from django.core.files.base import ContentFile
        import requests
        for countryData in jsonData:
            name = countryData["name"]
            code = countryData["code"]
            url = countryData["image"]
            _inst,ct= CountryDetails.objects.get_or_create(name=name,code=code)
            response = requests.get(url)
            _inst.image.save(url.split('/')[-1], ContentFile(response.content), save=True)
        

class VoiceLanguage(models.Model):

    name = models.CharField(max_length=50)
    country = models.ManyToManyField("CountryDetails")
    code = models.CharField(max_length=30,null=True,blank=True)
    tags = models.CharField(max_length=250,null=True,blank=True)
    image = models.FileField(upload_to='appAssets/language/',blank=True,null=True)

    def __str__(self):
        return self.name


class AvatarSoundCombination(models.Model):

    avatarImg = models.ForeignKey(AvatarImages, on_delete=models.CASCADE)
    avatarSound = models.ForeignKey(AvatarSounds, on_delete=models.CASCADE)

    video = models.FileField(upload_to='avatarCombination/')
    sound = models.FileField(upload_to='avatarCombination/')
    image = models.FileField(upload_to='avatarCombination/',blank=True,null=True)
    previewVideo = models.FileField(upload_to='avatarCombination/',blank=True,null=True)

    class Meta:
        unique_together = ('avatarImg', 'avatarSound',)

    def __str__(self):
        return f"{self.avatarImg.name}_{self.avatarSound.name}"