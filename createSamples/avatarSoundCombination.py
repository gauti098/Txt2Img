import json,os
from aiQueueManager.models import VideoRenderMultipleScene,AiTask
from appAssets.models import AvatarImages,AvatarSounds


_currentId = 555
_text = "Hi, I am glad to be your virtual agent."

allAvatarId = [4,5,6,7,8,9]
startSoundId = 1
startImageId = allAvatarId[5]
allAvatarSounds = AvatarSounds.objects.get(id=startSoundId)
allAvatarImages = AvatarImages.objects.get(id=startImageId)


mSceneInst = VideoRenderMultipleScene.objects.get(id=_currentId)
mSceneInst.avatar_image = allAvatarImages
mSceneInst.avatar_sound = allAvatarSounds
mSceneInst.save()


_aitaskInst = AiTask.objects.filter(text = _text).first()

print(_aitaskInst.id)
_aitaskInst.avatar_image = allAvatarImages
_aitaskInst.avatar_sound = allAvatarSounds
_aitaskInst.status = 3
_aitaskInst.save()

# generate manual Sound

# generate final video
allSceneInst = mSceneInst.singleScene.all()
texts = []
for tinst in allSceneInst:
    texts.append(tinst.getParsedText())
getUniqueData =mSceneInst.getUniqueDataM(texts)
_genStatus = mSceneInst.generateStatus
_genStatus.output = getUniqueData
_genStatus.status = 2
_genStatus.isVideoGenerated = False
_genStatus.isSoundGenerated = False
_genStatus.save()









'''
        if self.id == 1393:
            _movePath = f"/home/govind/VideoAutomation/src/uploads/avatar_sounds/samples/{self.multipleScene.avatar_image.id}_{self.multipleScene.avatar_sound.id}.mp4"
            _text = "Hi, I am glad to be your virtual agent."

            try:
                _curntGender = self.multipleScene.avatar_sound.gender
                for ii in range(self.multipleScene.avatar_sound.id+1,305):
                    allAvatarSounds = AvatarSounds.objects.get(id=ii)
                    if allAvatarSounds.gender == _curntGender:
                        break
                allAvatarImages = self.multipleScene.avatar_image
            except:
                allAvatarSounds = AvatarSounds.objects.get(id=1)
                try:
                    allAvatarImages = AvatarImages.objects.get(id=self.multipleScene.avatar_image.id+1)
                except:
                    return 0
            self.multipleScene.avatar_image = allAvatarImages
            self.multipleScene.avatar_sound = allAvatarSounds
            self.multipleScene.save()

            _aitaskInst = AiTask.objects.filter(text = _text).first()
            _aitaskInst.avatar_image = allAvatarImages
            _aitaskInst.avatar_sound = allAvatarSounds
            _aitaskInst.status = 3
            _aitaskInst.save()
            allSceneInst = self.multipleScene.singleScene.all()
            texts = []
            for tinst in allSceneInst:
                texts.append(tinst.getParsedText())
            getUniqueData =self.multipleScene.getUniqueDataM(texts)
            self.output = getUniqueData
            self.status = 2
            self.isVideoGenerated = False
            self.isSoundGenerated = False
            self.save()
            time.sleep(10)
            shutil.move(self.video.path,_movePath)
            
'''
