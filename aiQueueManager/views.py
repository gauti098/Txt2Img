from decimal import Context
import re,sys
from django import conf
from django.conf import settings
from numpy.lib.npyio import load
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.utils import timezone

from threading import Thread

from aiQueueManager.models import AiTask
from aiQueueManager.serializers import AiTaskSerializer

from utils.customValidators import isValidUrl

import subprocess,time
import numpy as np
import cv2,os

import json
import shutil


from glob import glob
import traceback
import cv2

from backgroundclip.models import ImageApiRes,VideoApiRes
from userlibrary.models import FileUpload
from django.db.models import Q

from django.core.files.base import ContentFile


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from uuid import uuid1,UUID
from datetime import datetime

from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob

from aiQueueManager.models import (
    AiTask,Colors,MergeTag,
    VideoRenderMultipleScene,
    VideoRenderSingleScene,SnapshotUrl,
    GeneratedFinalVideo,VideoThemeTemplate,
    VideoGradientColor
    )

from aiQueueManager.serializers import (
    AiTaskSerializer,MergeTagSerializer,
    VideoRenderMultipleSceneSerializer,
    VideoRenderSingleSceneSerializer,
    GenerateFinalVideoSerializer,SnapshotUrlSerializer,
    VideoDetailsSerializer,VideoThemeTemplateSerializer,
    VideoGradientColorSerializer
    )

from userlibrary.serializers import FileUploadSerializer
from videoThumbnail.models import MainThumbnail

from multiprocessing import Pool,Process




def extractBgFrame(bgPath,outputDir,totalFrames,fps=settings.VIDEO_DEFAULT_FPS):
    os.makedirs(outputDir,exist_ok=True)
    duration = totalFrames/fps
    _command = f"""ffmpeg -i {bgPath} -vf "fps=30" -to {duration} -start_number 0 -y {outputDir}/%05d.jpeg"""
    #cmd = subprocess.Popen(_command,cwd=os.path.dirname(bgPath), stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True).communicate()[0]
    #subprocess.call(_command, stdin=None, stdout=None, stderr=None, shell=False)

    #ffmpegPipe = subprocess.Popen(['ffmpeg','-i', bgPath,'-vf', "scale=(iw*sar)*max(1920/(iw*sar)\,1080/ih):ih*max(1920/(iw*sar)\,1080/ih), crop=1920:1080,fps=30", "-to", str(duration),"-start_number","0","-y",f"{outputDir}/%05d.jpeg"], stdin=subprocess.PIPE, stderr=subprocess.PIPE,shell=False)
    ffmpegPipe = subprocess.Popen(['ffmpeg','-i', bgPath,'-vf', "fps=30", "-to", str(duration),"-start_number","0","-y",f"{outputDir}/%05d.jpeg"], stdin=subprocess.PIPE, stderr=subprocess.PIPE,shell=False)
    out, err = ffmpegPipe.communicate()
    if out:
        out = out.decode()
    if err:
        err = err.decode()
    open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Extract Frame == {_command} == {out} == {err}\n")
    return 0 

def joinAllThread(inst,allThread):
    for cth in allThread:
        cth.join()
    inst.status = 3
    inst.save()



# def generateAiVideo(DEVICE=settings.DEVICE):
#     time.sleep(10)
#     melstepsize = settings.WAVLIPMELSTEPSIZE
#     allAvatarImgSeq = {}
#     try:
#         resQuery = GeneratedFinalVideo.objects.filter(Q(status=0) | Q(status=4))
#         for qq in resQuery:
#             qq.status = 2
#             qq.save()
#         while True:
#             try:
#                 query = GeneratedFinalVideo.objects.filter(status=2).order_by('isDefault','-priority')
#             except:
#                 time.sleep(10)
#                 continue
            
#             try:
#                 firstQueueData = query.first()
#                 isErrorFlag = False
#                 if firstQueueData:
#                     firstQueueData.setupTotalFrames()
#                     currentProcessingFrame = 0
                    

#                     firstQueueData.status = 4
#                     firstQueueData.save()
#                     print('Found New Task ',firstQueueData.id)
#                     allThread = []
#                     totalScene = firstQueueData.multipleScene.singleScene.all()
#                     totalSceneCount = totalScene.count() - 1
                    
#                     uniqueData = json.loads(firstQueueData.output)
#                     allScenes = uniqueData['scenes']
                    
#                     for crntSc,singleScene in enumerate(totalScene):
#                         print('Starting: ',crntSc,singleScene.id)
#                         try:
#                             queue_inst, created = AiTask.objects.get_or_create(avatar_image=firstQueueData.multipleScene.avatar_image,avatar_sound=firstQueueData.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
#                         except:
#                             queue_inst = AiTask.objects.filter(avatar_image=firstQueueData.multipleScene.avatar_image,avatar_sound=firstQueueData.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
#                             queue_inst.delete()
#                             queue_inst, created = AiTask.objects.get_or_create(avatar_image=firstQueueData.multipleScene.avatar_image,avatar_sound=firstQueueData.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
                        
#                         if queue_inst.text.strip() == '' or singleScene.videoThemeTemplate.name == "No Avatar":
#                             print('Inside No Text')
#                             queue_inst.status = 1
#                             queue_inst.totalOutputFrame = 1
#                             queue_inst.save()
#                             avatar_inst = queue_inst.avatar_image

#                             ## load first and last frame
#                             try:
#                                 _ = allAvatarImgSeq[avatar_inst.id][0]
#                             except:
#                                 allAvatarImgSeq[avatar_inst.id] = sorted(os.listdir(os.path.join(avatar_inst.getcwd(),'fullbody/without_swap/')))
                                
#                             startFrameIndx = 0
#                             aiStartFrame = queue_inst.start_frame
#                             aiOutputFolder = queue_inst.getFaceSwapDir()
#                             frame = os.path.join(avatar_inst.getcwd(),'fullbody/without_swap/',allAvatarImgSeq[avatar_inst.id][aiStartFrame+startFrameIndx])
#                             print('Inside No Text',frame,os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.png'))
#                             shutil.copy(frame,os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.png'))
#                             if firstQueueData.isDefault == True and (singleScene.bgVideoType == 3 or singleScene.bgVideoType == 4):
#                                 t = extractBgFrame(singleScene.getBgVideoPath(),singleScene.getBgVideoSeq(),queue_inst.totalOutputFrame)
                           
#                             currentProcessingFrame += queue_inst.totalOutputFrame
                            
#                         elif queue_inst.status != 1:
#                             print(f'Generating AI: {datetime.now()} {queue_inst.id} {firstQueueData.id}')
#                             queue_inst.status = 2
#                             queue_inst.save()

#                             avatar_inst = queue_inst.avatar_image

#                             isSound = queue_inst.generateSound()

#                             avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY = queue_inst.getAiPosition()
#                             avatarPosSize = avatarPosFX - avatarPosIX
                            


#                             #load mask
#                             aiVideoMask = cv2.VideoCapture(os.path.join(avatar_inst.getcwd(),'fullbody/mask.mp4'))
#                             aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, queue_inst.start_frame)
                            

#                             if isSound:
#                                 try:
#                                     print(f'Started Wav2Lip: {datetime.now()} {queue_inst.id} {firstQueueData.id}')
#                                     isMelChunk,mel_chunks = getMelChunks(os.path.join(queue_inst.getcwd(),'sound.wav'))
#                                     if not isMelChunk:
#                                         open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == {str(queue_inst.id)} == Wav2Lip == {mel_chunks}")
#                                         queue_inst.output = json.dumps({"wav2lip": {"status": False,"message": mel_chunks}})
#                                         queue_inst.status = 0
#                                         queue_inst.save()
#                                         firstQueueData.status = 0
#                                         firstQueueData.save()
#                                         isErrorFlag = True
#                                         break
                                    
#                                     mel_chunk_len = len(mel_chunks)

#                                     queue_inst.totalOutputFrame = mel_chunk_len
#                                     queue_inst.save()
#                                     #wav2lipConfig,avatarConfig = getVideoGenerateConfig(queue_inst,mel_chunks=mel_chunks)
#                                     #mainVideoGenerate(wav2lipConfig,avatarConfig)

#                                     if firstQueueData.isDefault == True and (singleScene.bgVideoType == 3 or singleScene.bgVideoType == 4):
#                                         print(f'Frame Extract: {datetime.now()} {queue_inst.id} {firstQueueData.id}')
#                                         ct = Thread(target=extractBgFrame,args=(singleScene.getBgVideoPath(),singleScene.getBgVideoSeq(),queue_inst.totalOutputFrame,))
#                                         ct.start()
#                                         allThread.append(ct)


#                                     avatarMainFolder =avatar_inst.getImageSeqPath()
#                                     aiOutputFolder = queue_inst.getFaceSwapDir()
#                                     ## load first and last frame
#                                     try:
#                                         _ = allAvatarImgSeq[avatar_inst.id][0]
#                                     except:
#                                         allAvatarImgSeq[avatar_inst.id] = sorted(os.listdir(avatarMainFolder))


#                                     drivingInit = torch.tensor(np.load(avatar_inst.getFirstInitFrame())).permute(0, 3, 1, 2).to(DEVICE)
#                                     sourceFrame = torch.tensor(np.load(avatar_inst.getSourceFrame())).permute(0, 3, 1, 2).to(DEVICE)
#                                     kpSourceFrame = settings.FIRSTORDERKPDETECTOR(sourceFrame)
#                                     kpDrivingInit = settings.FIRSTORDERKPDETECTOR(drivingInit)

#                                     startFrameIndx = 0
#                                     aiStartFrame = queue_inst.start_frame
                                    
                                    

#                                     # remove existing avatar data
#                                     try:
#                                         os.system(f"rm -rf {aiOutputFolder}*")
#                                     except:
#                                         pass


#                                     currentFrame = queue_inst.start_frame - 1

#                                     wav2lip_data_generator = wav2lip_datagen(mel_chunks,avatar_inst.getWav2lipVideo(),avatar_inst.getFaceCordinate(),queue_inst.start_frame,queue_inst.avatar_image.totalFrames)
#                                     wav2lipOutput = []
#                                     currentMaxBatch = 3000
#                                     for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(wav2lip_data_generator,total=int(np.ceil(float(mel_chunk_len)/settings.WAVLIPBATCHSIZE)))):
#                                         with torch.no_grad():
#                                             img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(DEVICE)
#                                             mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(DEVICE)
#                                             pred = settings.WAVLIPMODEL(mel_batch, img_batch)
#                                             pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.
#                                             for p, f, c in zip(pred, frames, coords):
#                                                 y1, y2, x1, x2 = c
#                                                 p = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
#                                                 f[y1:y2, x1:x2] = p

#                                                 drivingData = cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2RGB), (512,512))[..., :3].astype('float32')/255
#                                                 wav2lipOutput.append(drivingData)

#                                         if len(wav2lipOutput)>currentMaxBatch:
#                                             for drivingData in tqdm(wav2lipOutput,total=len(wav2lipOutput)):
#                                                 currentFrame += 1
#                                                 currentIndex = currentFrame%queue_inst.avatar_image.totalFrames
#                                                 with torch.no_grad():
#                                                     drivingDataT = torch.tensor(drivingData[np.newaxis]).permute(0,3,1,2).to(DEVICE)
#                                                     kpDriving = settings.FIRSTORDERKPDETECTOR(drivingDataT)
#                                                     kpNorm = normalize_kp(kp_source=kpSourceFrame, kp_driving=kpDriving,
#                                                                     kp_driving_initial=kpDrivingInit, use_relative_movement=True,
#                                                                     use_relative_jacobian=True, adapt_movement_scale=True)
                                                    
#                                                     fout = settings.FIRSTORDERGENERATOR(sourceFrame, kp_source=kpSourceFrame, kp_driving=kpNorm)
#                                                     aiRGBFrame = img_as_ubyte(np.transpose(fout['prediction'].data.cpu().numpy(), [0, 2, 3, 1])[0])

#                                                 aiRGBAFrame = cv2.cvtColor(aiRGBFrame,cv2.COLOR_RGB2RGBA)

#                                                 if currentIndex == 0 and currentFrame!=0:
#                                                     aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, currentIndex)
#                                                 ret,aiVideoMaskFrame = aiVideoMask.read()
#                                                 aiRGBAFrame[:,:,3] = aiVideoMaskFrame[:,:,1]
#                                                 aiRGBAFrame = cv2.resize(aiRGBAFrame,(avatarPosSize,avatarPosSize))
#                                                 if avatarPosIY<=0:
#                                                     aiRGBAFrame = aiRGBAFrame[avatarPosIY:avatarPosFY,avatarPosIX:avatarPosFX]
#                                                 ctAiProcess = Thread(target=saveAiSwapFrame, args=(os.path.join(avatarMainFolder,allAvatarImgSeq[avatar_inst.id][currentIndex]),aiRGBAFrame,(avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY),os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.webp'),))
#                                                 ctAiProcess.start()
#                                                 startFrameIndx+=1

#                                                 ## update progress in db
#                                                 if (currentProcessingFrame+startFrameIndx)%settings.VIDEO_PROGRESS_UPDATE_FRAME==0:
#                                                     firstQueueData.updateProgress(currentProcessingFrame+startFrameIndx)

#                                             wav2lipOutput = []
                                                    
#                                     gc.collect()
#                                     queue_inst.output = json.dumps({"wav2lip": {"status": True}})
#                                     queue_inst.save()
#                                     print(f'Wav2Lip Completed: {datetime.now()} {queue_inst.id} {firstQueueData.id}')

#                                     if len(wav2lipOutput)>0:
#                                         for drivingData in tqdm(wav2lipOutput,total=len(wav2lipOutput)):
#                                             currentFrame += 1
#                                             currentIndex = currentFrame%queue_inst.avatar_image.totalFrames
#                                             with torch.no_grad():
#                                                 drivingDataT = torch.tensor(drivingData[np.newaxis]).permute(0,3,1,2).to(DEVICE)
#                                                 kpDriving = settings.FIRSTORDERKPDETECTOR(drivingDataT)
#                                                 kpNorm = normalize_kp(kp_source=kpSourceFrame, kp_driving=kpDriving,
#                                                                 kp_driving_initial=kpDrivingInit, use_relative_movement=True,
#                                                                 use_relative_jacobian=True, adapt_movement_scale=True)
                                                
#                                                 fout = settings.FIRSTORDERGENERATOR(sourceFrame, kp_source=kpSourceFrame, kp_driving=kpNorm)
#                                                 aiRGBFrame = img_as_ubyte(np.transpose(fout['prediction'].data.cpu().numpy(), [0, 2, 3, 1])[0])

#                                             aiRGBAFrame = cv2.cvtColor(aiRGBFrame,cv2.COLOR_RGB2RGBA)
#                                             if currentIndex == 0 and currentFrame!=0:
#                                                 aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, currentIndex)
#                                             ret,aiVideoMaskFrame = aiVideoMask.read()
#                                             aiRGBAFrame[:,:,3] = aiVideoMaskFrame[:,:,1]
#                                             aiRGBAFrame = cv2.resize(aiRGBAFrame,(avatarPosSize,avatarPosSize))
#                                             if avatarPosIY<=0:
#                                                 aiRGBAFrame = aiRGBAFrame[avatarPosIY:avatarPosFY,avatarPosIX:avatarPosFX]
#                                             ctAiProcess = Thread(target=saveAiSwapFrame, args=(os.path.join(avatarMainFolder,allAvatarImgSeq[avatar_inst.id][currentIndex]),aiRGBAFrame,(avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY),os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.webp'),))
#                                             ctAiProcess.start()
#                                             startFrameIndx+=1

#                                             ## update progress in db
#                                             if (currentProcessingFrame+startFrameIndx)%settings.VIDEO_PROGRESS_UPDATE_FRAME==0:
#                                                 firstQueueData.updateProgress(currentProcessingFrame+startFrameIndx)
                                                

#                                             #if (min(currentProcessingFrame/firstQueueData.totalFrames,1)*100)%
#                                         gc.collect()
#                                     aiVideoMask.release()
#                                     allThread.append(ctAiProcess)
#                                     queue_inst.status = 1
#                                     queue_inst.output = json.dumps({"first_order": {"status": True}})
#                                     queue_inst.save()

#                                     currentProcessingFrame += queue_inst.totalOutputFrame
#                                     firstQueueData.updateProgress(currentProcessingFrame)
                                    
#                                 except Exception as e:
#                                     exc_type, exc_obj, exc_tb = sys.exc_info()
#                                     open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == {str(queue_inst.id)} == {str(e)}  ==  {str(exc_tb.tb_lineno)} == {str(traceback.format_exc())}\n\n")
#                                     queue_inst.output = json.dumps({"other": {"status": False,"message": str(e)}})
#                                     queue_inst.status = 0
#                                     queue_inst.save()
#                                     firstQueueData.status = 0
#                                     firstQueueData.save()
#                                     isErrorFlag = True
#                                     break
#                             else:
#                                 print('Error in Sound')
#                                 open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == {str(queue_inst.id)} == Sound == Error in Generating TTS")
#                                 queue_inst.output = json.dumps({"sound": {"status": False,"message": "Error in Generating TTS"}})
#                                 queue_inst.status = 0
#                                 firstQueueData.status = 0
#                                 firstQueueData.save()
#                                 queue_inst.save()
#                                 isErrorFlag = True
#                                 break
#                         else:

#                             if firstQueueData.isDefault == True and (singleScene.bgVideoType == 3 or singleScene.bgVideoType == 4):
#                                 ct = Thread(target=extractBgFrame,args=(singleScene.getBgVideoPath(),singleScene.getBgVideoSeq(),queue_inst.totalOutputFrame,))
#                                 ct.start()
#                                 allThread.append(ct)
#                             currentProcessingFrame += queue_inst.totalOutputFrame
#                             firstQueueData.updateProgress(currentProcessingFrame)

#                         uniqueData['scenes'][crntSc]['aitask'] = queue_inst.id
#                         uniqueData['scenes'][crntSc]['totalAvatarFrames'] = queue_inst.totalOutputFrame

#                     if isErrorFlag==False:
#                         for currentThread in allThread:
#                             currentThread.join()
#                         uniqueData['id']=firstQueueData.id
#                         uniqueData['isDefault']=firstQueueData.isDefault
#                         rabbitMQSendJob('electronCanvasRender',json.dumps(uniqueData),durable=True)
#                         firstQueueData.completedFrames = currentProcessingFrame
#                         firstQueueData.totalFrames = currentProcessingFrame
#                         firstQueueData.status = 3
#                         #firstQueueData.output=firstQueueData.multipleScene.getUniqueData()
#                         firstQueueData.save()
#                         firstQueueData.updateProgress(currentProcessingFrame)

                        
#                 else:
#                     #open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Query Not found == {str(traceback.format_exc())}\n\n")
#                     time.sleep(5)
#             except Exception as e:
#                 open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Try/Except Block == {str(traceback.format_exc())}\n\n")
#                 time.sleep(5)
#     except KeyboardInterrupt:
#         sys.exit()





# if settings.LOAD_GPU_MODEL:
#     from AiHandler.wav2lip import audio
#     from AiHandler.utils import normalize_kp,wav2lip_datagen,getMelChunks,saveAiSwapFrame
#     import torch
#     import gc
#     from scipy.spatial import ConvexHull
#     from skimage import img_as_ubyte
#     from tqdm import tqdm
#     aiT = Thread(target=generateAiVideo)
#     aiT.daemon = True
#     aiT.start()



class LimitOffset(LimitOffsetPagination):
    default_limit =10
    max_limit = 50


class VideoThemeTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoThemeTemplateSerializer


    def get(self, request, format=None):
        allQ = VideoThemeTemplate.objects.all()

        serializer = self.serializer_class(allQ,many=True)
        serializer.context['request']=request
        content = {'result': serializer.data}
        return Response(content,status=status.HTTP_200_OK)
        


class VideoThumbnailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    #serializer_class = VideoRenderMultipleScene

    def get_object(self, pk,user):
        try:
            return (True,VideoRenderMultipleScene.objects.get(pk=pk,user=user))
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def post(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            thubmbnailId = request.data.get('thumbnailId','')
            if thubmbnailId:
                try:
                    mainThumbnailInst = MainThumbnail.objects.get(id = int(thubmbnailId))
                    if mainThumbnailInst.category!=1:
                        if mainThumbnailInst.user.id != user.id:
                            content = {'thumbnailId': ['This Field is Not Valid.']}
                            return Response(content,status=status.HTTP_400_BAD_REQUEST)
                    inst.selectedThumbnail = mainThumbnailInst
                    inst.save()
                    inst.setThumbnail()
                    
                    return Response({"mergeTag": inst.getUsedMergeTag()},status=status.HTTP_200_OK)
                except:
                    content = {'thumbnailId': ['This Field is Not Valid.']}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                content = {'thumbnailId': ['This Field is Required.']}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)

        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class MergeTagDetailView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MergeTagSerializer

    def get_object(self, pk,user):
        try:
            return (True,MergeTag.objects.get(pk=pk,user=user))
        except MergeTag.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            serializer = self.serializer_class(inst)
            serializer.context['request']=request
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            data = request.data.copy()
            name = data.get('name')
            if name:
                if name[:2] == "{{" and name[-2:] == "}}":
                    name = name[2:-2]
                elif name[0] == '{' and name[-1] == '}':
                    name = name[1:-1]
                # name = ''.join(name.split())
                # if name[0] != '$':
                #     name = '$'+name
                data['name'] = "{{" + name + "}}"
            serializer = self.serializer_class(inst,data=data,partial=True)
            if serializer.is_valid():
                try:
                    serializer.save()
                    content = {'result': serializer.data}
                    return Response(content,status=status.HTTP_200_OK)
                except:
                    content = {'name': ['value already exists.']}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            inst.delete()
            return Response('ok',status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class MergeTagView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = MergeTagSerializer

    def get(self, request, format=None):
        user = request.user
        queryset = settings.DEFAULT_MERGE_TAG + list(MergeTag.objects.filter(user=user).values_list('name',flat=True)) 
        
        finalRes = [{'id': _id,"name": name,"value": name[2:-2]} for _id,name in enumerate(queryset)]
        content = {'results': finalRes}
        return Response(content,status=status.HTTP_200_OK)

    def post(self, request, format=None):
        user = request.user
        serializer = self.serializer_class(data=request.data,context={'request': request})
        if serializer.is_valid():
            serializer.save(user=user)
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)


# class ColorsDetailView(APIView,LimitOffset):
#     permission_classes = (IsAuthenticated,)
#     serializer_class = ColorsSerializer

#     def get_object(self, pk,user):
#         try:
#             return (True,Colors.objects.get(pk=pk,user=user))
#         except Colors.DoesNotExist:
#             return (False,'')

#     def get(self, request,pk, format=None):
#         user = request.user
#         is_exist,inst = self.get_object(pk,user)
#         if is_exist:
#             serializer = self.serializer_class(inst)
#             serializer.context['request']=request
#             content = {'result': serializer.data}
#             return Response(content,status=status.HTTP_200_OK)
#         else:
#             content = {'detail': 'Object Doestnot Exist'}
#             return Response(content,status=status.HTTP_404_NOT_FOUND)

#     def put(self, request,pk, format=None):
#         user = request.user
#         is_exist,inst = self.get_object(pk,user)
#         if is_exist:
#             serializer = self.serializer_class(inst,data=request.data,partial=True)
#             if serializer.is_valid():
#                 try:
#                     serializer.save()
#                     content = {'result': serializer.data}
#                     return Response(content,status=status.HTTP_200_OK)
#                 except:
#                     content = {'name': ['value already exists.']}
#                     return Response(content,status=status.HTTP_400_BAD_REQUEST)
#             else:
#                 return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
#         else:
#             content = {'detail': 'Object Doestnot Exist'}
#             return Response(content,status=status.HTTP_404_NOT_FOUND)


# class ColorsView(APIView,LimitOffset):
#     permission_classes = (IsAuthenticated,)
#     serializer_class = ColorsSerializer

#     def get_object(self, pk,user):
#         try:
#             return (True,VideoRenderMultipleScene.objects.get(pk=pk,user=user))
#         except VideoRenderMultipleScene.DoesNotExist:
#             return (False,'')

#     def get(self, request,pk, format=None):
#         user = request.user
#         is_exist,inst = self.get_object(pk,user)
#         if is_exist:
#             if inst.userColors:
#                 allColor = [i for i in inst.userColors.split(',')[::-1] if i] + settings.VIDEO_DEFAULT_COLOR
#             else:
#                 allColor = settings.VIDEO_DEFAULT_COLOR
#             return Response({'results': allColor},status=status.HTTP_200_OK)
#         else:
#             content = {'detail': 'Object Doestnot Exist'}
#             return Response(content,status=status.HTTP_404_NOT_FOUND)

#     def post(self, request,pk, format=None):
#         user = request.user
#         value = request.data.get('value','')
#         if value:
#             if value[0] != '#':
#                 value = '#'+value
#             is_exist,inst = self.get_object(pk,user)
#             if is_exist:
#                 match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value)
#                 if match:
#                     if inst.userColors:
#                         temp = inst.userColors.strip(',') + f",{value}"
#                     else:
#                         temp = f"{value}"
#                     inst.userColors = temp.strip(',')
#                     inst.save()
#                     return Response('ok',status=status.HTTP_200_OK)
#                 else:
#                     content = {'value': ['This Field is not Valid']}
#                     return Response(content,status=status.HTTP_400_BAD_REQUEST)
#             else:
#                 content = {'detail': 'Object Doestnot Exist'}
#                 return Response(content,status=status.HTTP_404_NOT_FOUND)

#         else:
#             content = {'value': ['This Field is Required']}
#             return Response(content,status=status.HTTP_400_BAD_REQUEST)
        


class VideoPublicTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderMultipleSceneSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','')
        filter = data.get('filter','')

        validOrder = {1: 'name',2: '-timestamp',3: 'timestamp',4: '-updated'}
        isOrder = None
        queryset = VideoRenderMultipleScene.objects.filter(isPublic=True,generateStatus__isnull=True)
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(Q(tags__icontains=filter) | Q(name__icontains=filter) | Q(descriptions__icontains=filter))

        if isOrder != None:
            queryset = queryset.order_by(isOrder)

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True)
        serializer.context['request']=request
        return self.get_paginated_response(serializer.data)


#Q(search_tags__contains=search_text) | Q(auto_tags__contains=search_text)
class VideoTemplateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderMultipleSceneSerializer

    def get(self, request, format=None):

        user = request.user
        data = request.GET
        orderId = data.get('order','')
        filter = data.get('filter','')

        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        queryset = VideoRenderMultipleScene.objects.filter(user=user,generateStatus__isnull=True)
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(Q(tags__icontains=filter) | Q(name__icontains=filter) | Q(descriptions__icontains=filter))

        if isOrder != None:
            queryset = queryset.order_by(isOrder)

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True)
        serializer.context['request']=request
        return self.get_paginated_response(serializer.data)

    # def post(self, request, format=None):
    #     user = request.user
    #     data = request.data

    #     if not user.is_staff:
    #         content = {'detail': 'User does not have enough permission'}
    #         return Response(content,status=status.HTTP_401_UNAUTHORIZED)
            
    #     serializer = self.serializer_class(data=data)
    #     if serializer.is_valid():
    #         currInst = serializer.save(user=user)
    #         serializer.context['request']=request
    #         return Response(serializer.data)
    #     else:
    #         return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)



# def takeScreenShot(url):
#     filename = str(uuid1())+'.png'
#     fullfilename = os.path.join("uploads/userlibrary/snapshot/",filename)
#     settings.CHROME_DRIVER.get(url)
#     settings.CHROME_DRIVER.get_screenshot_as_file(fullfilename)
#     return os.path.join("userlibrary/snapshot/",filename)


# SNAPSHOT_POOL = Pool(processes=1)
class SnapshotUrlView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = SnapshotUrlSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderSingleScene.objects.get(pk=pk)
            exist = currntInst.videorendermultiplescene_set.filter(user=user)
            if exist:
                return (True,currntInst)
            else:
                return (False,'')
        except:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        try:
            inst = SnapshotUrl.objects.get(id=pk)
            exist = inst.singleScene.videorendermultiplescene_set.filter(user=user)
            if exist:
                serializer = self.serializer_class(inst)
                serializer.context['request']=request
                content = {'result': serializer.data}
                return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Object Doestnot Exist'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        except:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def post(self, request,pk, format=None):
        user = request.user
        data = request.data
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            url = data.get('url',None)
            if url:
                isValid,url = isValidUrl(url)
                if isValid:
                    instSnap,created = SnapshotUrl.objects.get_or_create(url=url,singleScene=inst)
                    if created:
                        filename = str(uuid1())+'.jpeg'
                        outputPath = os.path.join(settings.BASE_DIR,"uploads/userlibrary/snapshot/",filename)
                        instSnap.image = outputPath.split(settings.MEDIA_ROOT)[1]
                        instSnap.save()
                    else:
                        try:
                            outputPath = instSnap.image.path
                        except:
                            pass
                        filename = str(uuid1())+'.jpeg'
                        outputPath = os.path.join(settings.BASE_DIR,"uploads/userlibrary/snapshot/",filename)
                        instSnap.image = outputPath.split(settings.MEDIA_ROOT)[1]
                        instSnap.save()
                    data = {"type": "videoCreateSnapshot","data": {"url": url,"outputPath": outputPath,"id": instSnap.id,"user": user.id}}
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "generateThumbnail",
                        {
                            "type": "setThumbnail",
                            "text": data,
                        },
                    )
                    ## await for generate
                    isFound = os.path.isfile(outputPath)
                    if isFound:
                        os.remove(outputPath)
                    for _ in range(10):
                        time.sleep(2)
                        isFound = os.path.isfile(outputPath)
                        if isFound:
                            serializer = self.serializer_class(instSnap,context={"request": request})
                            content = {'result': serializer.data}
                            return Response(content,status=status.HTTP_200_OK)

                    shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)
                    serializer = self.serializer_class(instSnap,context={"request": request})
                    content = {'result': serializer.data}
                    return Response(content,status=status.HTTP_200_OK)
                else:
                    content = {'url': ['url is not valid']}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                content = {'url': ['url field is required']}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
            

class VideoGradientView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoGradientColorSerializer

    def get(self, request, format=None):
        videoGradientQuery = VideoGradientColor.objects.all()
        videoGradient = VideoGradientColorSerializer(videoGradientQuery, many=True,context={'request': request})
        content = {'results': videoGradient.data}
        return Response(content,status=status.HTTP_200_OK)


class VideoTemplateDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderMultipleSceneSerializer

    def get_object(self, pk,user):
        try:
            return (True,VideoRenderMultipleScene.objects.get(pk=pk,user=user))
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            serializer = self.serializer_class(inst)
            serializer.context['request']=request
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            prevAvatar = inst.avatar_image.id
            reqData = request.data.copy()
            reqData.pop('singleScene','')
            _colors = reqData.pop("colors",None)
            if _colors:
                colorInst,ct = Colors.objects.get_or_create(user=user)
                colorInst.setColors(_colors)
                
            serializer = self.serializer_class(inst,data=reqData,partial=True,context={'request': request})
            if serializer.is_valid():
                inst = serializer.save()
                
                ## set thumbnail
                if inst.avatar_image.id!=prevAvatar:
                    outputPath = inst.thumbnailImage.path

                    uuidName = os.path.basename(outputPath)
                    try:
                        isValidUUid = UUID(uuidName.split('.')[0])
                        isFound = os.path.isfile(outputPath)
                        if isFound:
                            _oldPath = outputPath
                            #os.remove(outputPath)
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        if isFound:
                            shutil.copy(_oldPath,outputPath)
                    except:
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)

                    newFirstSceneInst = inst.singleScene.first()
                    newFirstSceneData = newFirstSceneInst.getUniqueDataM(None)
                    if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
                        extractBgFrame(newFirstSceneInst.getBgVideoPath(),newFirstSceneInst.getBgVideoSeqPublicPath(),2)#getBgVideoSeq(),2)
                    newFirstSceneData["outputPath"] = outputPath
                    newFirstSceneData.pop("text",None)
                    signalData = {"avatar_image": inst.avatar_image.id,"aiVideoUrl": inst.avatar_image.transparentImage.url,"scenes": [newFirstSceneData]}
                    rabbitMQSendJob('videoSceneToFabricJson',json.dumps(signalData),durable=True)
                    inst.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                    inst.save()

                content = {'result': serializer.data}
                return Response(content,status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            name = inst.name
            inst.delete()
            content = {'name': name,'isError': False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist','isError': False}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

class VideoTemplateCopyView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderMultipleSceneSerializer

    def get_object(self, pk):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk)
        if is_exist:
            if inst.user.id==user.id or inst.isPublic:
                serializerData = self.serializer_class(inst).data
                serializerData['singleScene'] = VideoRenderSingleSceneSerializer(inst.singleScene.all(),many=True).data
                for curInst in serializerData['singleScene']:
                    curInst['videoThemeTemplateData'] = json.dumps(curInst['videoThemeTemplateData'])
                    if curInst['snapshotData']:
                        curInst['snapshotData'] = curInst['snapshotData']['id']

                serializerData['name'] = f"Copy of {serializerData['name']}"
                newSerializer = self.serializer_class(data=serializerData,context={'request': request})
                if newSerializer.is_valid():
                    currInst = newSerializer.save(user=user)
                
                    currInst.save()
                    
                    ## set thumbnail
                    outputPath = currInst.thumbnailImage.path
                    uuidName = os.path.basename(outputPath)
                    try:
                        isValidUUid = UUID(uuidName.split('.')[0])
                        isFound = os.path.isfile(outputPath)
                        if isFound:
                            _oldPath = outputPath
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        if isFound:
                            shutil.copy(_oldPath,outputPath)
                    except:
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)

                    newFirstSceneInst = currInst.singleScene.first()
                    newFirstSceneData = newFirstSceneInst.getUniqueDataM(None)
                    if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
                        extractBgFrame(newFirstSceneInst.getBgVideoPath(),newFirstSceneInst.getBgVideoSeqPublicPath(),2)#getBgVideoSeq(),2)
                    newFirstSceneData["outputPath"] = outputPath
                    newFirstSceneData.pop("text",None)
                    signalData = {"avatar_image": currInst.avatar_image.id,"aiVideoUrl": currInst.avatar_image.transparentImage.url,"scenes": [newFirstSceneData]}
                    rabbitMQSendJob('videoSceneToFabricJson',json.dumps(signalData),durable=True)
                    currInst.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                    currInst.save()

                    content = {'result': newSerializer.data}
                    return Response(content,status=status.HTTP_200_OK)
                else:
                    return Response(newSerializer.errors,status=status.HTTP_400_BAD_REQUEST)
                
        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)



class VideoTemplateCreateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderMultipleSceneSerializer

    def get_object(self, pk):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request, format=None):
        user = request.user
        allPrevT = VideoRenderMultipleScene.objects.filter(user=user)
        if allPrevT:
            nameId = allPrevT.last().id
        else:
            nameId = 0
        
        # default Avatar
        getDA = AvatarImages.objects.first()
        getDS = AvatarSounds.objects.first()
        inst = VideoRenderMultipleScene(user=user,name=f'Video {nameId+1}',avatar_image=getDA,avatar_sound=getDS)
        inst.save()
        getThemeTemplate = VideoThemeTemplate.objects.get(name="Only Avatar")
        themeData = json.loads(getThemeTemplate.config)
        sceneData = themeData['default']
        sceneData['videoThemeTemplate'] = getThemeTemplate.id
        videoThemeTemplateData = json.dumps(themeData['themeData'])
        serializer = VideoRenderSingleSceneSerializer(data=sceneData,context={'request': request})
        if serializer.is_valid():
            currInst = serializer.save(videoThemeTemplateData=videoThemeTemplateData)
            inst.singleScene.add(currInst)
            multipleS = self.serializer_class(inst,context={'request': request})

            ## set thumbnail
            outputPath = inst.thumbnailImage.path
            uuidName = os.path.basename(outputPath)
            try:
                isValidUUid = UUID(uuidName.split('.')[0])
                isFound = os.path.isfile(outputPath)
                if isFound:
                    _oldPath = outputPath
                outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                if isFound:
                    shutil.copy(_oldPath,outputPath)
            except:
                outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)

            newFirstSceneInst = inst.singleScene.first()
            newFirstSceneData = newFirstSceneInst.getUniqueDataM(None)
            if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
                extractBgFrame(newFirstSceneInst.getBgVideoPath(),newFirstSceneInst.getBgVideoSeqPublicPath(),2)
            newFirstSceneData["outputPath"] = outputPath
            newFirstSceneData.pop("text",None)
            signalData = {"avatar_image": inst.avatar_image.id,"aiVideoUrl": inst.avatar_image.transparentImage.url,"scenes": [newFirstSceneData]}
            rabbitMQSendJob('videoSceneToFabricJson',json.dumps(signalData),durable=True)
            inst.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
            inst.save()
            return Response({'result': multipleS.data},status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)




class AllSingleSceneView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderSingleSceneSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            serializer = self.serializer_class(inst.singleScene.all(),many=True)
            serializer.context['request']=request
            content = {'results': serializer.data}
            return Response(content,status=status.HTTP_200_OK)
        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)

from appAssets.models import (
    AvatarImages,AvatarSounds,VoiceLanguage
)
from appAssets.serializers import (
    AvatarImagesSerializer,AvatarSoundsSerializer,VoiceLanguageSerializer
)
from backgroundclip.serializers import (
    ImageApiResSerializer,VideoApiResSerializer
)

def deserializeMultiScene(scenes,request):
    tempSc = {"upload": [],"apiImage": [],"apiVideo": [],"snapshotImage": []}

    tempCount = {} #{'bg':  {'bgVideoType': 0-5,'selectedIndex': None},'prsBg': {'prsBgType': 0-5,'selectedIndex': None},'logo': {'isLogo': False,'logo': None}}
    ## selected Data by Scene
    ## per scene {"bg": {"1": None,"2": None,"3": None,"4": None,"5": None}, "prsBg": {"1": None,"2": None}, "logo": None, "music": None}
    sceneData = {}

    for scene in scenes:
        sceneData[scene.id] = {"bg": {"1": None,"2": None,"3": None,"4": None,"5": None,"6": None}, "prsBg": {"1": None,"2": None,"6": None}, "logo": None, "music": None,"videoThemeTemplate": None}
        if scene.bgVideoType ==1:
            sData = ImageApiResSerializer(ImageApiRes.objects.get(id=scene.bgVideoID),context={'request': request}).data
            tempSc["apiImage"].append(sData)
            sceneData[scene.id]['bg']['1'] = sData

        elif scene.bgVideoType ==3:
            sData = VideoApiResSerializer(VideoApiRes.objects.get(id=scene.bgVideoID),context={'request': request}).data
            tempSc["apiVideo"].append(sData)
            sceneData[scene.id]['bg']['3'] = sData

        elif scene.bgVideoType ==2 or scene.bgVideoType ==4:
            sData = FileUploadSerializer(FileUpload.objects.get(id=scene.bgVideoID),context={'request': request}).data
            tempSc["upload"].append(sData)
            if scene.bgVideoType == 2:
                sceneData[scene.id]['bg']['2'] = sData
            else:
                sceneData[scene.id]['bg']['4'] = sData
           

        elif scene.bgVideoType ==5:
            if scene.isSnapshotMergeTag:
                sceneData[scene.id]['bg']['5'] = {"image": f'{settings.MEDIA_URL}{settings.VIDEO_SNAPSHOT_DEFAULT_IMAGE_PATH}'}
            else:
                sData = SnapshotUrlSerializer(SnapshotUrl.objects.get(id=scene.bgVideoID),context={'request': request}).data
                tempSc["snapshotImage"].append(sData)
                sceneData[scene.id]['bg']['5'] = sData

        elif scene.bgVideoType == 6:
            sData = VideoGradientColorSerializer(VideoGradientColor.objects.get(id=scene.bgVideoID),context={'request': request}).data
            sceneData[scene.id]['bg']['6'] = sData
        
        if scene.prsBgType ==1:
            sData = ImageApiResSerializer(ImageApiRes.objects.get(id=scene.prsBgImageId),context={'request': request}).data
            tempSc["apiImage"].append(sData)
            sceneData[scene.id]['prsBg']['1'] = sData

        elif scene.prsBgType ==2:
            sData = FileUploadSerializer(FileUpload.objects.get(id=scene.prsBgImageId),context={'request': request}).data
            tempSc["upload"].append(sData)
            sceneData[scene.id]['prsBg']['2'] = sData

        elif scene.prsBgType == 6:
            sData = VideoGradientColorSerializer(VideoGradientColor.objects.get(id=scene.prsBgImageId),context={'request': request}).data
            sceneData[scene.id]['prsBg']['6'] = sData
        
        if scene.logo:
            sData = FileUploadSerializer(FileUpload.objects.get(id=scene.logo.id),context={'request': request}).data
            tempSc["upload"].append(sData)
            sceneData[scene.id]['logo'] = sData

        if scene.music:
            sData = FileUploadSerializer(FileUpload.objects.get(id=scene.music.id),context={'request': request}).data
            tempSc["upload"].append(sData)
            sceneData[scene.id]['music'] = sData
        sceneData[scene.id]["videoThemeTemplate"] = VideoThemeTemplateSerializer(scene.videoThemeTemplate).data
        
    return tempSc,sceneData


class AllTemplateDataView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderSingleSceneSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            scenes = self.serializer_class(inst.singleScene.all(),many=True,context={'request': request}).data
            template = VideoRenderMultipleSceneSerializer(inst,context={'request': request}).data

            mergeQuery = list(MergeTag.objects.filter(user=user).values_list('name',flat=True)) + settings.DEFAULT_MERGE_TAG
            mergeTags = [{'id': _id,"name": name,"value": name[2:-2]} for _id,name in enumerate(mergeQuery)]
            

            colorInst,ct = Colors.objects.get_or_create(user=user)
            colors = colorInst.getColors()

            defaultSnapshotImageUrl = f'{settings.MEDIA_URL}{settings.VIDEO_SNAPSHOT_DEFAULT_IMAGE_PATH}'

            videoGradientQuery = VideoGradientColor.objects.all()
            videoGradient = VideoGradientColorSerializer(videoGradientQuery, many=True,context={'request': request}).data


            avatarImageQuery = AvatarImages.objects.all().filter(~Q(id__in=[1,2]))
            avatarImage = AvatarImagesSerializer(avatarImageQuery, many=True,context={'request': request}).data
            

            voiceLanguage = VoiceLanguageSerializer(inst.avatar_sound.voice_language,context={'request': request}).data
            
            avatarSoundQuery = AvatarSounds.objects.filter(voice_language= inst.avatar_sound.voice_language)
            
            _maleQuery = avatarSoundQuery.filter(gender=1)
            _femaleQuery = avatarSoundQuery.filter(gender=2)
            if inst.avatar_image.gender == 1:
                avatarSound = AvatarSoundsSerializer(_maleQuery, many=True,context={'request': request}).data
            else:
                avatarSound = AvatarSoundsSerializer(_femaleQuery, many=True,context={'request': request}).data

            videoTemplateQuery = VideoThemeTemplate.objects.all()
            videoTemplate = VideoThemeTemplateSerializer(videoTemplateQuery, many=True,context={'request': request}).data


            details,selectedData = deserializeMultiScene(inst.singleScene.all(),request)

            content = {'scenes': scenes,'template': template,'mergeTags': mergeTags,'colors': colors,'avatarImage': avatarImage,'avatarSound': avatarSound,'details': details,'selectedData': selectedData,'videoTemplate': videoTemplate,'defaultSnapshotImageUrl': defaultSnapshotImageUrl,'videoGradient': videoGradient,"voiceLanguage": voiceLanguage,'genderVoiceCount': {1: _maleQuery.count(),2: _femaleQuery.count()}}
            return Response(content,status=status.HTTP_200_OK)
        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)




## main Update View
class SingleSceneView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderSingleSceneSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderSingleScene.objects.get(pk=pk)
            if currntInst:
                exist = currntInst.videorendermultiplescene_set.filter(user=user)
                if exist:
                    return (True,currntInst,exist.first())
                else:
                    return (False,'','')
            else:
                return (False,'','')
        except VideoRenderSingleScene.DoesNotExist:
            return (False,'','')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst,multipleScene = self.get_object(pk,user)
        if is_exist:
            serializer = self.serializer_class(inst)
            serializer.context['request']=request
            content = {'result': serializer.data}
            return Response(content,status=status.HTTP_200_OK)

        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk, format=None):
        user = request.user
        data = request.data
        is_exist,inst,multipleScene = self.get_object(pk,user)
        if is_exist:
            data = data.copy()
            ownErrors = {}
            try:
                int(data['bgVideoID'])
            except:
                data.pop('bgVideoID')
            try:
                int(data['prsBgImageId'])
            except:
                data.pop('prsBgImageId')
            
            try:
                videoThemeTemplateData = data.pop('videoThemeTemplateData',None)
                if videoThemeTemplateData:
                    videoThemeTemplateData = json.dumps(videoThemeTemplateData)
            except:
                videoThemeTemplateData = None

            try:
                snapshotData = data.pop('snapshotData',0)
                if snapshotData!=0:
                    data['snapshotData'] = snapshotData['id']
            except:
                pass
            
            serializer = self.serializer_class(inst,data=data,partial=True,context={'request': request})
            if serializer.is_valid():
                ## own validation
                isError = False
                sData = serializer.validated_data

                # Validate template theme
                

                #handle Video Background
                bgvideoType = sData.get('bgVideoType')
                bgvideoID = sData.get('bgVideoID')
                bgColor = sData.get('bgColor')

                isBgChanged = False
                if bgvideoType or bgvideoID or bgColor:
                    isBgChanged = True
                if not bgvideoID:
                    bgvideoID = inst.bgVideoID
                if not bgvideoType:
                    bgvideoType = inst.bgVideoType
                if isBgChanged:
                    if bgvideoType == 0:
                        if not bgColor:
                            bgColor = inst.bgColor
                        # if multipleScene.userColors:
                        #     allColor = multipleScene.userColors.split(',')[::-1] + settings.VIDEO_DEFAULT_COLOR
                        # else:
                        #     allColor = settings.VIDEO_DEFAULT_COLOR
                        # if bgColor not in allColor:
                        #     ownErrors['bgColor'] = ["This Field is Required."]
                        #     isError = True
                    elif bgvideoType == 1:
                        try:
                            _inst = ImageApiRes.objects.get(id=bgvideoID)
                            _inst.is_save = True
                            _inst.save()
                        except:
                            ownErrors['bgVideoID'] = ["id is not valid"]
                            isError = True
                    elif bgvideoType == 2:
                        try:
                            _inst = FileUpload.objects.get(id=bgvideoID)
                            if not _inst.isPublic and _inst.user.id!=user.id:
                                ownErrors['bgVideoID'] = ["id is not valid"]
                                isError = True
                            else:
                                if _inst.media_type.split('/')[0] != 'image':
                                    ownErrors['bgVideoID'] = ["media is not a valid image"]
                                    isError = True
                        except:
                            ownErrors['bgVideoID'] = ["id is not valid"]
                            isError = True
                    elif bgvideoType == 3:
                        try:
                            _inst = VideoApiRes.objects.get(id=bgvideoID)
                            _inst.is_save = True
                            _inst.save()
                        except:
                            ownErrors['bgVideoID'] = ["id is not valid"]
                            isError = True
                    elif bgvideoType == 4:
                        try:
                            _inst = FileUpload.objects.get(id=bgvideoID)
                            if not _inst.isPublic and _inst.user.id!=user.id:
                                ownErrors['bgVideoID'] = ["id is not valid"]
                                isError = True
                            else:
                                if _inst.media_type.split('/')[0] != 'video':
                                    ownErrors['bgVideoID'] = ["media is not a valid video"]
                                    isError = True
                        except:
                            ownErrors['bgVideoID'] = ["id is not valid"]
                            isError = True
                    elif bgvideoType == 5:
                        isSnapshotMergeTag = sData.get('isSnapshotMergeTag')
                        if not isSnapshotMergeTag:
                            isSnapshotMergeTag = inst.isSnapshotMergeTag
                        if not isSnapshotMergeTag:
                            try:
                                _inst = SnapshotUrl.objects.get(id=bgvideoID)
                            except:
                                ownErrors['bgVideoID'] = ["id is not valid"]
                                isError = True


                ## handle person Background
                prsBgType = sData.get('prsBgType')
                prsBgImageId = sData.get('prsBgImageId')
                prsBgColor = sData.get('prsBgColor')
                isPrsBgChanged = False
                if prsBgType or prsBgImageId or prsBgColor:
                    isPrsBgChanged = True
                if not prsBgImageId:
                    prsBgImageId = inst.prsBgImageId
                if not prsBgType:
                    prsBgType = inst.prsBgType
                if isPrsBgChanged:
                    if prsBgType == 0:
                        if not prsBgColor:
                            prsBgColor = inst.prsBgColor
                        # if multipleScene.userColors:
                        #     allColor = multipleScene.userColors.split(',')[::-1] + settings.VIDEO_DEFAULT_COLOR
                        # else:
                        #     allColor = settings.VIDEO_DEFAULT_COLOR
                        # if prsBgColor not in allColor:
                        #     ownErrors['prsBgColor'] = ["This Field is Required."]
                        #     isError = True
                    elif prsBgType == 1:
                        try:
                            _inst = ImageApiRes.objects.get(id=prsBgImageId)
                            _inst.is_save = True
                            _inst.save()
                        except:
                            ownErrors['prsBgImageId'] = ["id is not valid"]
                            isError = True
                    elif prsBgType == 2:
                        try:
                            _inst = FileUpload.objects.get(id=prsBgImageId)
                            if not _inst.isPublic and _inst.user.id!=user.id:
                                ownErrors['prsBgImageId'] = ["id is not valid"]
                                isError = True
                            else:
                                if _inst.media_type.split('/')[0] != 'image':
                                    ownErrors['prsBgImageId'] = ["media is not a valid image"]
                                    isError = True
                        except:
                            ownErrors['prsBgImageId'] = ["id is not valid"]
                            isError = True
                

                #handle logo
                logo = sData.get('logo')
                isLogo = sData.get('isLogo')
                if not isLogo:
                    isLogo = inst.isLogo
                if logo:
                    if not logo.isPublic and logo.user.id!=user.id:
                        ownErrors['logo'] = ["id is not valid"]
                        isError = True
                    else:
                        if logo.media_type.split('/')[0] != 'image':
                            ownErrors['logo'] = ["logo is not a valid image"]
                            isError = True
                else:
                    logo = inst.logo

                if isLogo:
                    if not logo:
                        ownErrors['logo'] = ["isLogo is Enabled But logo is not Selected"]
                        isError = True


                #handle music
                music = sData.get('music')
                isMusic = sData.get('isMusic')
                if not isMusic:
                    isMusic = inst.isMusic
                if music:
                    if not music.isPublic and music.user.id!=user.id:
                        ownErrors['music'] = ["id is not valid"]
                        isError = True
                    else:
                        if music.media_type.split('/')[0] != 'audio':
                            ownErrors['music'] = ["id is not valid"]
                            isError = True
                else:
                    music = inst.music
                if isMusic==1:
                    if not music:
                        ownErrors['music'] = ["isMusic is Enabled But Music is not Selected"]
                        isError = True
                

                if isError:
                    return Response(ownErrors,status=status.HTTP_400_BAD_REQUEST)

                if videoThemeTemplateData:
                    inst = serializer.save(videoThemeTemplateData=videoThemeTemplateData)
                else:
                    inst = serializer.save()

                content = {'result': serializer.data}
                return Response(content,status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)

    def delete(self, request,pk, format=None):
        user = request.user
        is_exist,inst,multipleScene = self.get_object(pk,user)
        if is_exist:
            firstSceneId = multipleScene.singleScene.first().id
            deleteSceneId = inst.id
            if multipleScene.singleScene.all().count()==1:
                return Response({'message': 'Cannot Delete Single Scene'},status=status.HTTP_200_OK)
            else:
                inst.delete()
                if firstSceneId==deleteSceneId:
                    ## set thumbnail
                    outputPath = multipleScene.thumbnailImage.path
                    uuidName = os.path.basename(outputPath)
                    try:
                        isValidUUid = UUID(uuidName.split('.')[0])
                        isFound = os.path.isfile(outputPath)
                        if isFound:
                            _oldPath = outputPath
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        if isFound:
                            shutil.copy(_oldPath,outputPath)
                        
                    except:
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")

                    newFirstSceneInst = multipleScene.singleScene.first()
                    newFirstSceneData = newFirstSceneInst.getUniqueDataM(None)
                    if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
                        extractBgFrame(newFirstSceneInst.getBgVideoPath(),newFirstSceneInst.getBgVideoSeqPublicPath(),2)
                    newFirstSceneData["outputPath"] = outputPath
                    newFirstSceneData.pop("text",None)
                    signalData = {"avatar_image": multipleScene.avatar_image.id,"aiVideoUrl": multipleScene.avatar_image.transparentImage.url,"scenes": [newFirstSceneData]}
                    rabbitMQSendJob('videoSceneToFabricJson',json.dumps(signalData),durable=True)
                    multipleScene.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                    multipleScene.save()
                return Response('ok',status=status.HTTP_200_OK)

        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)


#all update View
class VideoTemplateSaveView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderSingleSceneSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def put(self, request,pk, format=None):
        user = request.user
        data = request.data
        is_exist,minst = self.get_object(pk,user)
        ## watch thumbnail Changed
        prevFirstSceneData = minst.singleScene.first().getUniqueDataM(None)
        if is_exist:
            try:
                finalError = []
                for singleScene in data:
                    singleScene = singleScene.copy()
                    try:
                        scId = singleScene.pop('id')
                        inst = minst.singleScene.get(id=scId)
                    except:
                        finalError.append({'data': singleScene,'error': 'id not Valid','isSave': False})
                        continue

                    ownErrors = {}

                    try:
                        int(singleScene['bgVideoID'])
                    except:
                        singleScene.pop('bgVideoID')
                    try:
                        int(singleScene['prsBgImageId'])
                    except:
                        singleScene.pop('prsBgImageId')

                    try:
                        videoThemeTemplateData = singleScene.pop('videoThemeTemplateData',None)
                        if videoThemeTemplateData:
                            videoThemeTemplateData = json.dumps(videoThemeTemplateData)
                    except:
                        videoThemeTemplateData = None
                    
                    try:
                        snapshotData = singleScene.pop('snapshotData',0)
                        if snapshotData!=0:
                            singleScene['snapshotData'] = snapshotData['id']
                    except:
                        pass

                    serializer = self.serializer_class(inst,data=singleScene,partial=True,context={'request': request})
                    if serializer.is_valid():
                        ## own validation
                        isError = False
                        sData = serializer.validated_data

                        # Validate template theme
                        

                        #handle Video Background
                        bgvideoType = sData.get('bgVideoType')
                        bgvideoID = sData.get('bgVideoID')
                        bgColor = sData.get('bgColor')

                        isBgChanged = False
                        if bgvideoType or bgvideoID or bgColor:
                            isBgChanged = True
                        if not bgvideoID:
                            bgvideoID = inst.bgVideoID
                        if not bgvideoType:
                            bgvideoType = inst.bgVideoType
                        if isBgChanged:
                            if bgvideoType == 0:
                                if not bgColor:
                                    bgColor = inst.bgColor
                                if bgColor[0]!='#':
                                    bgColor="#"+bgColor
                            elif bgvideoType == 1:
                                try:
                                    _inst = ImageApiRes.objects.get(id=bgvideoID)
                                    _inst.is_save = True
                                    _inst.save()
                                except:
                                    ownErrors['bgVideoID'] = ["id is not valid"]
                                    isError = True
                            elif bgvideoType == 6:
                                try:
                                    _inst = VideoGradientColor.objects.get(id=bgvideoID)
                                except:
                                    ownErrors['bgVideoID'] = ["id is not valid"]
                                    isError = True
                            elif bgvideoType == 2:
                                try:
                                    _inst = FileUpload.objects.get(id=bgvideoID)
                                    if not _inst.isPublic and _inst.user.id!=user.id:
                                        ownErrors['bgVideoID'] = ["id is not valid"]
                                        isError = True
                                    else:
                                        if _inst.media_type.split('/')[0] != 'image':
                                            ownErrors['bgVideoID'] = ["media is not a valid image"]
                                            isError = True
                                except:
                                    ownErrors['bgVideoID'] = ["id is not valid"]
                                    isError = True
                            elif bgvideoType == 3:
                                try:
                                    _inst = VideoApiRes.objects.get(id=bgvideoID)
                                    _inst.is_save = True
                                    _inst.save()
                                    
                                except:
                                    ownErrors['bgVideoID'] = ["id is not valid"]
                                    isError = True
                            elif bgvideoType == 4:
                                try:
                                    _inst = FileUpload.objects.get(id=bgvideoID)
                                    if not _inst.isPublic and _inst.user.id!=user.id:
                                        ownErrors['bgVideoID'] = ["id is not valid"]
                                        isError = True
                                    else:
                                        if _inst.media_type.split('/')[0] != 'video':
                                            ownErrors['bgVideoID'] = ["media is not a valid video"]
                                            isError = True
                                except:
                                    ownErrors['bgVideoID'] = ["id is not valid"]
                                    isError = True
                            elif bgvideoType == 5:
                                isSnapshotMergeTag = sData.get('isSnapshotMergeTag')
                                if not isSnapshotMergeTag:
                                    isSnapshotMergeTag = inst.isSnapshotMergeTag
                                if not isSnapshotMergeTag:
                                    try:
                                        _inst = SnapshotUrl.objects.get(id=bgvideoID)
                                    except:
                                        ownErrors['bgVideoID'] = ["id is not valid"]
                                        isError = True


                        ## handle person Background
                        prsBgType = sData.get('prsBgType')
                        prsBgImageId = sData.get('prsBgImageId')
                        prsBgColor = sData.get('prsBgColor')
                        isPrsBgChanged = False
                        if prsBgType or prsBgImageId or prsBgColor:
                            isPrsBgChanged = True
                        if not prsBgImageId:
                            prsBgImageId = inst.prsBgImageId
                        if not prsBgType:
                            prsBgType = inst.prsBgType
                        if isPrsBgChanged:
                            if prsBgType == 0:
                                if not prsBgColor:
                                    prsBgColor = inst.prsBgColor
                                if prsBgColor[0]!='#':
                                    prsBgColor="#"+prsBgColor
                            elif prsBgType == 1:
                                try:
                                    _inst = ImageApiRes.objects.get(id=prsBgImageId)
                                    _inst.is_save = True
                                    _inst.save()
                                except:
                                    ownErrors['prsBgImageId'] = ["id is not valid"]
                                    isError = True
                            elif prsBgType == 6:
                                try:
                                    _inst = VideoGradientColor.objects.get(id=prsBgImageId)
                                except:
                                    ownErrors['prsBgImageId'] = ["id is not valid"]
                                    isError = True
                            elif prsBgType == 2:
                                try:
                                    _inst = FileUpload.objects.get(id=prsBgImageId)
                                    if not _inst.isPublic and _inst.user.id!=user.id:
                                        ownErrors['prsBgImageId'] = ["id is not valid"]
                                        isError = True
                                    else:
                                        if _inst.media_type.split('/')[0] != 'image':
                                            ownErrors['prsBgImageId'] = ["media is not a valid image"]
                                            isError = True
                                except:
                                    ownErrors['prsBgImageId'] = ["id is not valid"]
                                    isError = True
                        

                        #handle logo
                        logo = sData.get('logo')
                        isLogo = sData.get('isLogo')
                        if not isLogo:
                            isLogo = inst.isLogo
                        if logo:
                            if not logo.isPublic and logo.user.id!=user.id:
                                ownErrors['logo'] = ["id is not valid"]
                                isError = True
                            else:
                                if logo.media_type.split('/')[0] != 'image':
                                    ownErrors['logo'] = ["logo is not a valid image"]
                                    isError = True
                        else:
                            logo = inst.logo

                        if isLogo:
                            if not logo:
                                ownErrors['logo'] = ["isLogo is Enabled But logo is not Selected"]
                                isError = True


                        #handle music
                        music = sData.get('music')
                        isMusic = sData.get('isMusic')
                        if not isMusic:
                            isMusic = inst.isMusic
                        if music:
                            if not music.isPublic and music.user.id!=user.id:
                                ownErrors['music'] = ["id is not valid"]
                                isError = True
                            else:
                                if music.media_type.split('/')[0] != 'audio':
                                    ownErrors['music'] = ["id is not valid"]
                                    isError = True
                        else:
                            music = inst.music
                        if isMusic==1:
                            if not music:
                                ownErrors['music'] = ["isMusic is Enabled But Music is not Selected"]
                                isError = True
                        

                        if isError:
                            finalError.append({'data': singleScene,'error': ownErrors,'isSave': False})
                            continue
                        
                        if videoThemeTemplateData:
                            inst = serializer.save(videoThemeTemplateData=videoThemeTemplateData)
                        else:
                            inst = serializer.save()
                        
                        finalError.append({'data': serializer.data,'isSave': True})
                        
                    else:
                        finalError.append({'data': singleScene,'error': serializer.errors,'isSave': False})
                ## set draft thubmbnail
                newFirstSceneInst = minst.singleScene.first()
                newFirstSceneData = newFirstSceneInst.getUniqueDataM(None)
                outputPath = minst.thumbnailImage.path
                if json.dumps(newFirstSceneData)!=json.dumps(prevFirstSceneData) or len(outputPath.split('default.jpg'))>1:
                    if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
                        if newFirstSceneData['bgVideoType'] != prevFirstSceneData['bgVideoType'] or newFirstSceneData['bgVideoID'] != prevFirstSceneData['bgVideoID']:
                            ## extract single frame
                            extractBgFrame(newFirstSceneInst.getBgVideoPath(),newFirstSceneInst.getBgVideoSeqPublicPath(),2)
                    ## check imagepath is not default
                    
                    uuidName = os.path.basename(outputPath)
                    try:
                        isValidUUid = UUID(uuidName.split('.')[0])
                        isFound = os.path.isfile(outputPath)
                        if isFound:
                            _oldPath = outputPath
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        if isFound:
                            shutil.copy(_oldPath,outputPath)
                        
                    except:
                        outputPath = outputPath.replace(uuidName,f"{uuid1()}.jpeg")
                        shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)
                    newFirstSceneData["outputPath"] = outputPath
                    newFirstSceneData.pop("text",None)
                    signalData = {"avatar_image": minst.avatar_image.id,"aiVideoUrl": minst.avatar_image.transparentImage.url,"scenes": [newFirstSceneData]}
                    rabbitMQSendJob('videoSceneToFabricJson',json.dumps(signalData),durable=True)
                    minst.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
                    minst.save()
                return Response(finalError,status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'message': f'Bad Data {e}'},status=status.HTTP_400_BAD_REQUEST)
        else:    
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)




class SingleSceneAddView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoRenderSingleSceneSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            lastScene = inst.singleScene.last()
            getThemeTemplate = VideoThemeTemplate.objects.get(name="Only Avatar")
            themeData = json.loads(getThemeTemplate.config)
            prevData = themeData['default']

            videoThemeTemplateData = json.dumps(themeData['themeData'])
            if lastScene:
                if lastScene.isMusic==-1 or lastScene.isMusic==1:
                    prevData['isMusic'] = -1
                if lastScene.isLogo:
                    prevData['isLogo'] = True
                    prevData['logo'] = lastScene.logo.id
                prevData['text'] = ""

            prevData['videoThemeTemplate'] = getThemeTemplate.id
            serializer = self.serializer_class(data=prevData,context={'request': request})
            if serializer.is_valid():
                currInst = serializer.save(videoThemeTemplateData=videoThemeTemplateData)
                inst.singleScene.add(currInst)
                details,selectedData = deserializeMultiScene([currInst],request)
                content = {'result': serializer.data,'selectedData': selectedData}
                return Response(content,status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        content = {'detail': 'Object Doestnot Exist'}
        return Response(content,status=status.HTTP_404_NOT_FOUND)


class BackgroundMusicView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = FileUploadSerializer

    def get(self, request, format=None):

        queryset = FileUpload.objects.filter(isPublic=True,category="bgMusic") #| FileUpload.objects.filter(user=request.user,category="bgMusic").order_by('-timestamp')
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class GeneratingVideoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GenerateFinalVideoSerializer

    def get(self, request, format=None):

        data = request.GET
        orderId = data.get('order','')
        filter = data.get('filter','')

        validOrder = {0: 'name', 1: '-name',2: 'updated',3: '-updated', 4: 'timestamp',5: '-timestamp'}
        isOrder = None
        queryset = VideoRenderMultipleScene.objects.filter(user=request.user,generateStatus__isnull=False).filter(generateStatus__isDefault=True)
        if orderId:
            try:
                isOrder = validOrder[int(orderId)]
            except:
                pass
        if filter:
            queryset = queryset.filter(Q(tags__icontains=filter) | Q(name__icontains=filter) | Q(descriptions__icontains=filter))

        if isOrder != None:
            queryset = queryset.order_by(isOrder)
    
        results = self.paginate_queryset(queryset, request, view=self)
        results = [i.generateStatus for i in results]
        serializer = self.serializer_class(results, many=True,context={'request': request})
        return self.get_paginated_response(serializer.data)



class VideoDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoDetailsSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')


    def get(self, request,pk, format=None):

        user= request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            sData = self.serializer_class(inst,context={'request': request}).data
            if inst.generateStatus:
                sData['mergeTags'] = inst.getUsedMergeTag()
                content = {'result': sData}
                return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'detail': 'Cannot see Details Without Generated.'}
                return Response(content,status=status.HTTP_404_NOT_FOUND)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk, format=None):

        user = request.user
        data = request.data.copy()
        is_exist,inst = self.get_object(pk,user)
        if is_exist:

            serializer = self.serializer_class(inst, data=data,partial=True,context={'request': request})
            isValid = serializer.is_valid()
            if isValid:
                cinst = serializer.save()
                sData = self.serializer_class(cinst,context={'request': request}).data
            
                sData['mergeTags'] = inst.getUsedMergeTag()
                content = {'result': sData}
                return Response(content,status=status.HTTP_200_OK)
            else:
                allErr = {}
                if not isValid:
                    allErr = serializer.errors
                return Response(allErr,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)






class GeneratingVideoDetailsView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GenerateFinalVideoSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):

        user= request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if inst.generateStatus:
                content = {'result': self.serializer_class(inst.generateStatus,context={'request': request}).data}
            else:
                content = {'detail': "Generate Video To Check Status."}
            return Response(content,status=status.HTTP_200_OK)    
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class GenerateVideoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GenerateFinalVideoSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if (user.totalVideoCredit - user.usedVideoCredit)<=0:
                content = {'message': 'Not Enough Video Credit'}
                return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            if user.subs_end:
                if timezone.now()>user.subs_end:
                    content = {'message': 'Subscriptions End'}
                    return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            else:
                content = {'message': 'Subscriptions End'}
                return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)


            prevGenS = inst.generateStatus
            if prevGenS:
                if prevGenS.status==2 or prevGenS.status==3 or prevGenS.status==4:
                    content = {'result': self.serializer_class(prevGenS,context={'request': request}).data,'message': 'Video Already Generating'}
                    return Response(content,status=status.HTTP_200_OK)
            allSceneInst = inst.singleScene.all()
            texts = []
            for tinst in allSceneInst:
                texts.append(tinst.getParsedText())
            getUniqueData =inst.getUniqueDataM(texts)

            finalGInstQ = GeneratedFinalVideo.objects.filter(multipleScene=inst,output=getUniqueData,status=1)
            if finalGInstQ.count()>=1:
                finalGInst = finalGInstQ.first()
                if finalGInst.name != inst.name or finalGInst.isDefault!=1:
                    finalGInst = GeneratedFinalVideo.objects.get_or_create(name=inst.name,isDefault=1,multipleScene=inst,output=getUniqueData,video=finalGInst.video,status=1)
                    finalGInst.save()
                    finalGInst.onVideoComplete()
            else:
                finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=inst.name,multipleScene=inst,output=getUniqueData,isDefault=1)
            

            ## set draft thubmbnail
            outputPath = inst.thumbnailImage.path
            thubmbnailUrl = inst.thumbnailImage.url
            
            if len(outputPath.split('default.jpg'))>1:
                uuidName = f"{uuid1()}.jpeg"
                outputPath = outputPath.replace('default.jpg',uuidName)
            else:
                uuidName = os.path.basename(outputPath)

            ## create MainThumbnail
            allSceneThumbnail = []
            signalData = {"avatar_image": inst.avatar_image.id,"aiVideoUrl": inst.avatar_image.transparentImage.url,"scenes": []}
            for indx,singleScInst in enumerate(inst.singleScene.all()):
                newFirstSceneData = singleScInst.getUniqueDataM(None)
                if newFirstSceneData['bgVideoType'] == 3 or newFirstSceneData['bgVideoType'] == 4:
                    extractBgFrame(singleScInst.getBgVideoPath(),singleScInst.getBgVideoSeqPublicPath(),2)
                
                newFirstSceneData["outputPath"] = outputPath.replace(uuidName,f"scene_{indx}_{uuidName}")
                

                thumbInst = MainThumbnail(user = user,name = f"Scene {indx+1}",category=0,thumbnailImage=newFirstSceneData["outputPath"].split(settings.MEDIA_ROOT)[1])
                thumbInst.save()
                allSceneThumbnail.append(thumbInst)


                newFirstSceneData['thumbnailId'] = thumbInst.id
                newFirstSceneData.pop("text",None)
                signalData['scenes'].append(newFirstSceneData)

            try:
                shutil.copy(inst.thumbnailImage.path,allSceneThumbnail[0].thumbnailImage.path)
            except:
                shutil.copy(os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,'loading.jpg'),outputPath)


            inst.selectedThumbnail = allSceneThumbnail[0]
            inst.sceneThumbnails.add(*allSceneThumbnail)
            inst.thumbnailImage = allSceneThumbnail[0].thumbnailImage
            finalGInst.thumbnailImage = allSceneThumbnail[0].thumbnailImage
            finalGInst.save()

            rabbitMQSendJob('videoSceneToFabricJson',json.dumps(signalData),durable=True)

            inst.generateStatus = finalGInst
            inst.save()
        
            content = {'result': self.serializer_class(finalGInst,context={'request': request}).data,'message': 'Video Started Generating'}
            return Response(content,status=status.HTTP_200_OK)    
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)



class VideoDetailsGeneratingView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GenerateFinalVideoSerializer

    def get_object(self, pk,user):
        try:
            currntInst = GeneratedFinalVideo.objects.get(pk=pk,multipleScene__user=user)
            return (True,currntInst)
        except GeneratedFinalVideo.DoesNotExist:
            return (False,'')

    def get(self, request,pk, format=None):

        user= request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            content = {'result': self.serializer_class(inst,context={'request': request}).data}
            return Response(content,status=status.HTTP_200_OK)    
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


class VideoDetailsGenerateView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    serializer_class = GenerateFinalVideoSerializer

    def get_object(self, pk,user):
        try:
            currntInst = VideoRenderMultipleScene.objects.get(pk=pk,user=user)
            return (True,currntInst)
        except VideoRenderMultipleScene.DoesNotExist:
            return (False,'')


    def get(self, request,pk, format=None):

        user= request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            query = GeneratedFinalVideo.objects.filter(multipleScene=inst,isDefault=2).order_by('-timestamp')
            results = self.paginate_queryset(query, request, view=self)
            serializer = self.serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)


    def post(self, request,pk, format=None):
        user = request.user
        is_exist,inst = self.get_object(pk,user)
        if is_exist:
            if (user.totalVideoCredit - user.usedVideoCredit)<=0:
                content = {'detail': 'Not Enough Video Credit'}
                return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            if user.subs_end:
                if timezone.now()>user.subs_end:
                    content = {'detail': 'Subscriptions End'}
                    return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)
            else:
                content = {'detail': 'Subscriptions End'}
                return Response(content,status=status.HTTP_402_PAYMENT_REQUIRED)

            allTag = inst.getUsedMergeTag()
            errors = {"name": ''}
            isError = False
            name = request.data.get('name')
            allMV = {}
            if not name:
                errors['name'] = "This Field is Required"
                isError = True
            
            for mtag in allTag:
                mname = mtag['name']
                mnamev = request.data.get(mname)
                if not mnamev:
                    errors[mname] = "This Field is Required"
                    isError = True
                else:
                    ## check tag value not be greater than 250 char
                    if len(mnamev)>=250:
                        errors[mname] = "Character Limit Exceeded! (Max Limit: 250 Char)"
                        isError = True
                    if mname == "{{WebsiteScreenshot}}":
                        isValid,mnamev = isValidUrl(mnamev)
                        if not isValid:
                            errors[mname] = "This Field is not Valid"
                            isError = True
                allMV[mname] = mnamev


            isVideoBg = False
                
            allSceneInst = inst.singleScene.all()
            texts = []
            for tinst in allSceneInst:
                texts.append(tinst.getCustomParsedText(allMV))
                if tinst.isSnapshotMergeTag and tinst.bgVideoType==5:
                    isVideoBg = True

            if isError:
                content = {'errors': errors}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)

            getUniqueData = inst.getUniqueDataM(texts)
            if isVideoBg:
                getUniqueData = json.loads(getUniqueData)
                getUniqueData['{{WebsiteScreenshot}}'] = allMV["{{WebsiteScreenshot}}"]
                getUniqueData = json.dumps(getUniqueData)

            finalGInstQ = GeneratedFinalVideo.objects.filter(multipleScene=inst,output=getUniqueData,status=1)
            created = False
            if finalGInstQ.count()>=1:
                finalGInst = finalGInstQ.first()
                if finalGInst.name != name or finalGInst.isDefault!=2:
                    finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=name,isDefault=2,multipleScene=inst,output=getUniqueData,video=finalGInst.video,status=1,videoUsedMergeTag = json.dumps(allMV))
                    if created:
                        finalGInst.onVideoComplete()
            else:
                finalGInst,created = GeneratedFinalVideo.objects.get_or_create(name=name,multipleScene=inst,output=getUniqueData,isDefault=2,videoUsedMergeTag = json.dumps(allMV))

            if created:
                finalGInst.thumbnailImage = inst.thumbnailImage
                finalGInst.save()
                finalGInst.setThumbnail()
            
            # if isThumbnailSnapshot==False:
            #     finalGInst.thumbnailImage = inst.generateStatus.thumbnailImage
            #     finalGInst.save()
            # else:
            #     outputPath = os.path.join(finalGInst.getThumbnailPath(),f"{uuid1()}.jpeg")
                
            #     data = {"type": "setSalesPageCampaignThumbnail","data": {"url": allMV["{WebsiteScreenshot}"],"outputPath": outputPath}}
            #     channel_layer = get_channel_layer()
            #     async_to_sync(channel_layer.group_send)(
            #         "generateThumbnail",
            #         {
            #             "type": "setThumbnail",
            #             "text": data,
            #         },
            #     )
            #     finalGInst.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
            #     finalGInst.save()
                

            content = {'result': self.serializer_class(finalGInst,context={'request': request}).data}
            return Response(content,status=status.HTTP_200_OK)

        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)
