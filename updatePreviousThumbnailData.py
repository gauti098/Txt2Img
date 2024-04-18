
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from uuid import uuid1,UUID
from aiQueueManager.models import (
    AiTask,Colors,MergeTag,
    VideoRenderMultipleScene,
    VideoRenderSingleScene,
    GenerateFullVideo,VideoTextTemplate,SnapshotUrl,
    GeneratedFinalVideo,VideoThemeTemplate
    )
from videoThumbnail.models import MainThumbnail
import os
from django.conf import settings
import time
from aiQueueManager.views import extractBgFrame
a = MainThumbnail.objects.all()

#a.delete()
queryset = VideoRenderMultipleScene.objects.filter(generateStatus__isnull=False)
totalCc = queryset.count()


for iii,inst in enumerate(queryset):
    outputPath = inst.thumbnailImage.path
    thubmbnailUrl = inst.thumbnailImage.url
    print(inst.id,iii,totalCc)
    
    if len(outputPath.split('default.jpg'))>1:
        uuidName = f"{uuid1()}.jpeg"
        outputPath = outputPath.replace('default.jpg',uuidName)
    else:
        uuidName = os.path.basename(outputPath)
    allSceneThumbnail = []
    signalData = {"type": "draftVideo","data": {"avatar_image": inst.avatar_image.id,"aiVideoUrl": inst.avatar_image.transparentImage.url,"scenes": []}}
    for indx,singleScInst in enumerate(inst.singleScene.all()):
        newFirstSceneData = singleScInst.getUniqueDataM(None)
        if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
            extractBgFrame(singleScInst.getBgVideoPath(),singleScInst.getBgVideoSeqPublicPath(),2)
                
        newFirstSceneData["outputPath"] = outputPath.replace(uuidName,f"scene_{indx}_{uuidName}")

        thumbInst = MainThumbnail(user = inst.user,name = f"Scene {indx+1}",category=0,thumbnailImage=newFirstSceneData["outputPath"].split(settings.MEDIA_ROOT)[1])
        thumbInst.save()
        allSceneThumbnail.append(thumbInst)


        newFirstSceneData['thumbnailId'] = thumbInst.id
        signalData['data']['scenes'].append(newFirstSceneData)


    print(len(allSceneThumbnail))
    inst.selectedThumbnail = allSceneThumbnail[0]
    inst.save()
    inst.sceneThumbnails.clear()
    inst.sceneThumbnails.add(*allSceneThumbnail)
    inst.save()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "generateThumbnail",
        {
            "type": "setThumbnail",
            "text": signalData,
        },
    )
    inst.save()
    time.sleep(3)