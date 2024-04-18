import json
from celery import shared_task
from django.db import connection
from django_celery_results.models import TaskResult
from newVideoCreator import models as newVideoCreatorModels
from backgroundclip import models as backgroundclipModels
from backgroundclip import serializers as backgroundclipSerializers
from django.conf import settings

from newVideoCreator.utils.generateSceneMusic import generateAudioWithSeprateMusic
from utils.common import convertFloat, convertInt

@shared_task(bind=True)
def extractVideoFrames(self,data):
    _videoId = data["videoId"]
    try:
        _crntQuery = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoId)
        _taskInst = _crntQuery.videoCreator
        _videoData = json.loads(_taskInst._videoData)
        _sceneData = json.loads(_taskInst.parseData)

        _sceneArr = _sceneData["sceneArr"]
        _aiSceneInst = None
        _isSceneAnimation = None
        for _sceneIndex in _sceneArr:
            _allVideoId = _videoData["sceneWiseData"].get(_sceneIndex,None)
            if _allVideoId:
                for _videoId in _allVideoId:
                    _inst = backgroundclipModels.APISaveVideo.objects.get(id=_videoId)
                    if not _inst.isVideoProcessed:
                        _inst.extractFrames()
                        _videoData["videoInfo"][_videoId] = backgroundclipSerializers.APISaveVideoServerSideSerializer(_inst).data
            # update db and send signal, completed frame extract of scene
            if _aiSceneInst and _isSceneAnimation:
                _aiSceneInst.sendJobToVideoRender()

            _isSceneAnimation = _videoData["isSceneAnimation"].get(_sceneIndex,False)
            _aiSceneInst = _crntQuery.aiSceneGenerate.get(sceneIndex=int(_sceneIndex))
            _videoData["processed"][f"{_sceneIndex}"] = True
            _taskInst._videoData = json.dumps(_videoData)
            _taskInst.save()

            if not _isSceneAnimation:
                _aiSceneInst.sendJobToVideoRender()
        return True
    except Exception as e:
        return f"Video Frame Extract Error: {_videoId}, {e}"


@shared_task(bind=True)
def sceneRenderComplete(self,sceneIndex,data={}):
    try:
        _inst = newVideoCreatorModels.AiVideoSceneGenerate.objects.get(pk=sceneIndex)
        if data and _inst.videoCreator.objTagData:
            _prevData = json.loads(_inst.videoCreator.objTagData)
            _prevData[f"{_inst.sceneIndex}"]["sceneInfo"] = data
            _inst.videoCreator.objTagData = json.dumps(_prevData)
            _inst.videoCreator.save()
        _inst.onRenderComplete()
        return True
    except Exception as e:
        return f"Video Render Complete Error: {sceneIndex}, {e}"


# from newVideoCreator.serializers import  VideoCreatorSerializer
import newVideoCreator
from events import fire
@shared_task(bind=True)
def addVideoToGenerate(self,_id):
    try:
        _inst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_id)
        _inst.setDefaultMergeTag()
        _inst.videoCreator.addDefaultSalesPage()
        _inst.addSceneToAiTask()
        _inst.saveAllThumbnail()
        _inst.videoCreator.updateAllMergeTag()
        
        # exract video frames
        extractVideoFrames.delay({"videoId": _id})
       
        _inst.setThumbnail()
        commandData = newVideoCreator.serializers.VideoCreatorSerializer(_inst.videoCreator).data
        fire.eventFire(_inst.videoCreator.user,"videoEditor.list.add",commandData)

        if not _inst.isSoundGenerated:
            try:
                generateAudioWithSeprateMusic(_id)
            except Exception as e:
                print(f"Video Audio Generate Error: {_id}, {e}")
    except Exception as e:
        return f"addVideoToGenerate Error: {_id}, {e}"


@shared_task(bind=True)
def mainVideoAudioGenerate(self,_mainGenerateId):
    try:
        generateAudioWithSeprateMusic(_mainGenerateId)
        return True
    except Exception as e:
        return f"Video Audio Generate Error: {_mainGenerateId}, {e}"

from createSamples import addAvatarSoundSample
@shared_task(bind=True)
def tempTask(self,videoCId):
    try:
        _inst = newVideoCreatorModels.MainVideoGenerate.objects.get(videoCreator__pk=int(videoCId),generationType=0)
        _inst.delete()
    except:
        pass

    addAvatarSoundSample.generateVideoSample(int(videoCId))


from videoCredit import models as VideoCreditModels
from django.contrib.auth import get_user_model
import math
@shared_task(bind=True)
def addCreditTask(self,creditInfo):
    userSubscriptionInst = None
    try:
        user = get_user_model().objects.get(id=creditInfo.pop("userId",None))
        userSubscriptionInst,ct = VideoCreditModels.UserCurrentSubscription.objects.get_or_create(user=user)
        _type = creditInfo.pop("type")
        usedCredit = convertInt(creditInfo.pop("usedCredit",1),1)
        if _type == "AVATAR_VIDEO" or _type == "NON_AVATAR_VIDEO":
            _duration = convertFloat(creditInfo.get("duration"))
            usedCredit =  math.ceil(_duration/settings.VIDEOCREDIT_RATE)

        userSubscriptionInst.subscriptionValidator(_type,usedCredit,creditInfo)
        return True
    except:
        return False
    