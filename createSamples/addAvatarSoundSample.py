import os
from appAssets.models import AvatarSounds
from newVideoCreator import models as newModels #import TempVideoCreator,MainVideoGenerate
import time
from shutil import move,copy



# avatarId = 7#6#5
# crntVideoId = 2778#2777#2776
def moveFile(fileP,avatarId,soundId):
    _samplePath = '/home/govind/VideoAutomation/src/uploads/avatar_sounds/'
    try:
        copy(fileP,os.path.join(_samplePath,f'samples/{avatarId}_{soundId}.mp4'))
        move(fileP,os.path.join(_samplePath,f'crntSample/{avatarId}_{soundId}.mp4'))
    except:
        pass

def getSoundId(crntVideoId):
    ID_MAPP = {2771: 4,2776: 5,2777:6,2778:7,2779:8,2780:9 }
    GENDER = {4: 2,5: 2,6: 2,7: 2,8: 1,9: 1}
    avatarId = ID_MAPP.get(crntVideoId,False)
    if avatarId==False:
        return False

    allSoundInst = AvatarSounds.objects.filter(gender=GENDER[avatarId]).order_by('id')
    _samplePath = '/home/govind/VideoAutomation/src/uploads/avatar_sounds/'
    _allGeneratedSamples = os.listdir(os.path.join(_samplePath,'samples'))
    allGeneratedSamples = []
    for ii in _allGeneratedSamples:
        if ii.split('_')[0]==f'{avatarId}':
            allGeneratedSamples.append(int(ii.split('.')[0].split('_')[-1]))


    _allGeneratedSamples1 = os.listdir(os.path.join(_samplePath,'crntSample'))
    for ii in _allGeneratedSamples1:
        if ii.split('_')[0]==f'{avatarId}':
            allGeneratedSamples.append(int(ii.split('.')[0].split('_')[-1]))

    allGeneratedSamples = sorted(allGeneratedSamples)
    nextGenerateId = []
    for ii in allSoundInst:
        if ii.id not in allGeneratedSamples:
            nextGenerateId.append(ii.id)
            return ii.id
            
    return False

def generateVideoSample(crntVideoId):
    soundId = getSoundId(crntVideoId)
    print(soundId)
    if soundId:
        _inst = newModels.TempVideoCreator.objects.get(id=crntVideoId)
        _gInst,ct = newModels.MainVideoGenerate.objects.get_or_create(videoCreator=_inst)
        _inst.mainVideoGenerate = _gInst
        _inst.save()
        _inst.updateAvatarSound(soundId)
        _inst.mainVideoGenerate.generateVideo(isForced=True)

'''
from createSamples.addAvatarSoundSample import generateVideoSample
generateVideoSample(2771)

crntVideoId=2778
soundId = 58
_inst = newModels.TempVideoCreator.objects.get(id=crntVideoId)

if _inst.mainVideoGenerate:
    _inst.mainVideoGenerate.delete()

_gInst,ct = newModels.MainVideoGenerate.objects.get_or_create(videoCreator=_inst)
_inst.mainVideoGenerate = _gInst
_inst.save()
_inst.updateAvatarSound(soundId)
_inst.mainVideoGenerate.generateVideo()

avatarId=9
allSoundInst = AvatarSounds.objects.all().order_by('id')
_samplePath = '/home/govind/VideoAutomation/src/uploads/avatar_sounds/'
_allGeneratedSamples = os.listdir(os.path.join(_samplePath,'samples'))
allGeneratedSamples = []
for ii in _allGeneratedSamples:
    if ii.split('_')[0]==f'{avatarId}':
        allGeneratedSamples.append(int(ii.split('.')[0].split('_')[-1]))


_allGeneratedSamples1 = os.listdir(os.path.join(_samplePath,'crntSample'))
for ii in _allGeneratedSamples1:
    if ii.split('_')[0]==f'{avatarId}':
        allGeneratedSamples.append(int(ii.split('.')[0].split('_')[-1]))

allGeneratedSamples = sorted(allGeneratedSamples)
nextGenerateId = []
for ii in allSoundInst:
    if ii.id not in allGeneratedSamples:
        nextGenerateId.append(ii.id)

print(len(nextGenerateId))
'''

