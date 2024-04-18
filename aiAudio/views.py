from datetime import date
import json
import time
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from aiAudio.models import AiAudio, AiCombineAudio
from appAssets.models import AvatarSounds
from aiQueueManager.models import VideoRenderMultipleScene
from aiAudio.serializers import AiAudioSerializer,AiCombineAudioSerializer
from uuid import uuid4
import os
from multiprocessing import Pool
from threading import Thread
import logging
import traceback
from utils.common import convertInt, getParsedText

from utils.common import convertFloat

logger = logging.getLogger(__name__)

    
def aiGenerateSound(aiAudioId,isInst=False):
    if isInst:
        aiAudioInst = aiAudioId
    else:
        aiAudioInst = AiAudio.objects.get(pk=aiAudioId)
    return aiAudioInst.aiGenerateSound()


class AiAudioGenerateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AiAudioSerializer

    def get_object(self, pk):
        try:
            return (True,AiAudio.objects.get(pk=pk))
        except AiAudio.DoesNotExist:
            return (False,'')

    def post(self, request, format=None):
        reqData = request.data
        try:
            allParseData = []
            allThread = []
            isError = False
            errorMessage = []
            for singleR in reqData:
                try:
                    soundInst = AvatarSounds.objects.get(id=int(singleR.get("avatarSound")))
                    try:
                        aiAudioInst,ct = AiAudio.objects.get_or_create(avatarSound=soundInst,text=getParsedText(singleR.get("text","")))
                        if ct:
                            aiAudioInst.user = request.user
                            aiAudioInst.save()
                            
                        allParseData.append(aiAudioInst.pk)
                        _thread = Thread(target=aiGenerateSound, args=(aiAudioInst.pk,))
                        _thread.start()
                        allThread.append(_thread)
                        errorMessage.append({"isError": False,"message": ""})
                    except:
                        isError = True
                        errorMessage.append({"isError": True,"text": "Unable to parse or Character Limit (max character 5000)."})
                except:
                    isError = True
                    errorMessage.append({"isError": True,"avatarSound": "This Field does not exist."})
            if isError:
                content = {'detail': errorMessage,"isError": True}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)

            # with Pool(processes=len(allParseData)) as pool:
            #     multiple_results = [pool.apply_async(aiGenerateSound, (_currentData,)) for _currentData in allParseData]
            #     for _index,curInst in enumerate(multiple_results):
            #         _ = curInst.get()
            for ct in allThread:
                ct.join()

            finalResult = [AiAudio.objects.get(pk=_id) for _id in allParseData]
            serializer = self.serializer_class(finalResult,many=True,context={'request': request})
            content = {'results': serializer.data,"isError": False}
            return Response(content,status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(str(traceback.format_exc()))
            content = {'detail': 'Unable to Parse Requests.',"isError": True}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)




class AiAudioGenerateWithCombinationView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AiCombineAudioSerializer


    def post(self, request, format=None):
        reqData = request.data
        try:
            allParseData = []
            allThread = []
            isError = False
            errorMessage = []
            allAudioInfo = []
            customId = []
            isCustomId = False
            for singleR in reqData:
                try:
                    soundInst = AvatarSounds.objects.get(id=int(singleR.get("avatarSound")))
                    _text = singleR.get("text","")
                    _cid = singleR.get("_id",None)
                    customId.append(_cid)
                    if _cid!=None:
                        isCustomId = True
                    #if _text:
                    try:
                        _delay = convertFloat(singleR.get("delay",0))
                        if _delay>20:
                            isError = True
                            errorMessage.append({"isError": True,"delay": "Delay must be less than 20."})
                            continue
                        aiAudioInst,ct = AiAudio.objects.get_or_create(avatarSound=soundInst,text=getParsedText(_text))
                        if ct:
                            aiAudioInst.user = request.user
                            aiAudioInst.save()
                        allParseData.append(aiAudioInst.pk)
                        allAudioInfo.append({"id": aiAudioInst.id,"delay": _delay})
                        _thread = Thread(target=aiGenerateSound, args=(aiAudioInst.pk,))
                        _thread.start()
                        allThread.append(_thread)
                        errorMessage.append({"isError": False,"message": ""})
                    except:
                        isError = True
                        errorMessage.append({"isError": True,"text": "Unable to parse or Character Limit (max character 5000)."})
                    # else:
                    #     isError = True
                    #     errorMessage.append({"isError": True,"text": "This Field is Required."})
                except:
                    isError = True
                    errorMessage.append({"isError": True,"avatarSound": "This Field does not exist."})
            if isError:
                content = {'detail': errorMessage,"isError": True}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)

            for ct in allThread:
                ct.join()

            allInst = [AiAudio.objects.get(pk=_id) for _id in allParseData]
            _combineInst,ct = AiCombineAudio.objects.get_or_create(allAudioInfo=json.dumps(allAudioInfo))
            if ct:
                _combineInst.user = request.user
                _combineInst.save()
            else:
                if _combineInst.isGenerated:
                    serializer = self.serializer_class(_combineInst,context={'request': request})
                    _combineAll = AiAudioSerializer(allInst,many=True,context={'request': request}).data
                    content = {'results': _combineAll,'combineData': serializer.data,"isError": False}
                    if isCustomId:
                        _modifiedData = []
                        for _ind,_elm in enumerate(_combineAll):
                            _elm['_id'] = customId[_ind]
                            _modifiedData.append(_elm)
                        content["results"] = _modifiedData
                    return Response(content,status=status.HTTP_200_OK) 
            isSuccess =_combineInst.combineMultipleAiAudio(allInst,allAudioInfo)
            if isSuccess:
                serializer = self.serializer_class(_combineInst,context={'request': request})
                _combineAll = AiAudioSerializer(allInst,many=True,context={'request': request}).data
                content = {'results': _combineAll,'combineData': serializer.data,"isError": False}
                if isCustomId:
                    _modifiedData = []
                    for _ind,_elm in enumerate(_combineAll):
                        _elm['_id'] = customId[_ind]
                        _modifiedData.append(_elm)
                    content["results"] = _modifiedData
                return Response(content,status=status.HTTP_200_OK)
            else:
                content = {'deatil': "Unable to Combine Audio","isError": True}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(str(traceback.format_exc()))
            content = {'detail': 'Unable to Parse Requests.',"isError": True}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)



def batchGenerateSound(request,allParseData,allAudioInfo,_combineInstWithCt):
    allThread = []
    for _audioInstId in allParseData:
        _thread = Thread(target=aiGenerateSound, args=(_audioInstId,))
        _thread.start()
        allThread.append(_thread)

    for ct in allThread:
        ct.join()
    allInst = [AiAudio.objects.get(pk=_id) for _id in allParseData]
    _combineInst,ct = _combineInstWithCt
    if ct:
        _combineInst.user = request.user
        _combineInst.save()
    else:
        if _combineInst.isGenerated:
            return True
    isSuccess =_combineInst.combineMultipleAiAudio(allInst,allAudioInfo)
    return isSuccess


class BatchAudioGenerateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AiCombineAudioSerializer


    def post(self, request, format=None):
        mainData = request.data
        if len(mainData)>15:
            content = {'detail': 'Audio Batch Limit Exceeded.',"isError": True}
            return Response(content,status=status.HTTP_400_BAD_REQUEST)
        _alreadyQueryAudioInst = {}
        allThread = []
        _finalAllParseData = []
        _finalCombineInst = []
        _finalCustomId = []
        _finalResults = [-1]*len(mainData)
        _allThreadIndx = []
        for _indx,reqData in enumerate(mainData):
            try:
                allParseData = []
                isError = False
                errorMessage = []
                allAudioInfo = []
                customId = []
                isCustomId = False
                for singleR in reqData:
                    try:
                        ## fetch avatar inst
                        _audioInstId = convertInt(singleR.get("avatarSound"),None)
                        if _audioInstId==None:
                            isError = True
                            errorMessage.append({"isError": True,"avatarSound": f"avatarSound is not valid."})
                            continue
                        else:
                            try:
                                if not _alreadyQueryAudioInst.get(_audioInstId,False):
                                    soundInst = AvatarSounds.objects.get(id=_audioInstId)
                                    _alreadyQueryAudioInst[_audioInstId] = soundInst
                            except:
                                isError = True
                                errorMessage.append({"isError": True,"avatarSound": f"avatarSound is not valid."})
                                continue
                        
                        ## handle text
                        _text = singleR.get("text","")
                        if len(_text)>settings.AVATAR_AUDIO_CHARACTER_LIMIT and len(_text)>5000:
                            isError = True
                            errorMessage.append({"isError": True,"text": f"text must be less than {settings.AVATAR_AUDIO_CHARACTER_LIMIT}."})
                            continue
                        
                        ## handle for sending with id
                        _cid = singleR.get("_id",None)
                        customId.append(_cid)
                        if _cid!=None:
                            isCustomId = True


                        _delay = convertFloat(singleR.get("delay",0))
                        if _delay>20:
                            isError = True
                            errorMessage.append({"isError": True,"delay": "Delay must be less than 20."})
                            continue
                        
                        try:
                            aiAudioInst,ct = AiAudio.objects.get_or_create(avatarSound=_alreadyQueryAudioInst[_audioInstId],text=getParsedText(_text))
                        except:
                            allInsttt = AiAudio.objects.filter(avatarSound=_alreadyQueryAudioInst[_audioInstId],text=getParsedText(_text))
                            allInsttt.delete()
                            aiAudioInst,ct = AiAudio.objects.get_or_create(avatarSound=_alreadyQueryAudioInst[_audioInstId],text=getParsedText(_text))

                        if ct:
                            aiAudioInst.user = request.user
                            aiAudioInst.save()

                        allParseData.append(aiAudioInst.pk)
                        allAudioInfo.append({"id": aiAudioInst.id,"delay": _delay})
                        errorMessage.append({"isError": False,"message": ""})
                    except:
                        logger.error(str(traceback.format_exc()))
                        isError = True
                        errorMessage.append({"isError": True,"message": "Some Issue Occured."})

                if isError:
                    content = {'detail': errorMessage,"isError": True}
                    #_finalError.append(content)
                    _finalResults[_indx] = content
                    continue

                _combineInst,_combineInstCt = AiCombineAudio.objects.get_or_create(allAudioInfo=json.dumps(allAudioInfo))
                _thread = Thread(target=batchGenerateSound, args=(request,allParseData,allAudioInfo,(_combineInst,_combineInstCt),))
                _thread.start()
                allThread.append(_thread)
                _finalAllParseData.append(allParseData)
                _finalCombineInst.append(_combineInst)
                _finalCustomId.append((isCustomId,customId))
                _allThreadIndx.append(_indx)

            except Exception as e:
                logger.error(str(traceback.format_exc()))
                content = {'detail': 'Unable to Parse Requests.',"isError": True}
                _finalResults[_indx]=content
                #return Response(content,status=status.HTTP_400_BAD_REQUEST)

        
        for _index,_mainIndx in enumerate(_allThreadIndx):
            allThread[_index].join()
            allParseData = _finalAllParseData[_index]
            allInst = [AiAudio.objects.get(pk=_id) for _id in allParseData]
            _combineInst = _finalCombineInst[_index]
            isCustomId,customId = _finalCustomId[_index]
            if _combineInst.isGenerated:
                serializer = self.serializer_class(_combineInst,context={'request': request})
                _combineAll = AiAudioSerializer(allInst,many=True,context={'request': request}).data
                content = {'results': _combineAll,'combineData': serializer.data,"isError": False}
                if isCustomId:
                    _modifiedData = []
                    for _ind,_elm in enumerate(_combineAll):
                        _elm['_id'] = customId[_ind]
                        _modifiedData.append(_elm)
                    content["results"] = _modifiedData
                _finalResults[_mainIndx] = content
            else:
                content = {'deatil': "Unable to Combine Audio","isError": True}
                _finalResults[_mainIndx] = content

        return Response(_finalResults,status=status.HTTP_200_OK)
        