import json
from django.conf import settings
from backgroundclip.models import APISaveVideo
from newVideoCreator import models as newVideoCreatorModels
from moviepy.editor import AudioFileClip, AudioClip, CompositeAudioClip, concatenate_audioclips
from moviepy.audio.fx.all import volumex, audio_loop

from userlibrary import models as userlibraryModels
from utils.common import convertFloat
import traceback
import logging 
logger = logging.getLogger(__name__)
'''
Adjust Length
    0 => nothing
    1 => loop
    2 => freeze frame
    3 => adjust as scene
'''
# music adjust_length 1=> current,4=>loop in all scene

def generateAudio1(_videoGenId):
    try:
        _videoGenInst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoGenId)
        _parseData = json.loads(_videoGenInst.videoCreator.parseData)
        sceneIndex = _parseData["sceneArr"]
        
        sceneData = _parseData["data"]
        finalAudioList = []
        crntTotalDuration = 0

        allSceneAudioData = {}
        for _scId in sceneIndex:
            _sceneInst = _videoGenInst.aiSceneGenerate.get(sceneIndex=_scId)
            _audioPath = _sceneInst.avatarSound
            _crntData = sceneData[_scId]
            _allVideo = _crntData["musicInfo"]["video"].copy()
            totalSceneDuration = round(sceneData[_scId]["totalSceneDuration"],2)
            _avatarAudioClip = None
            _avatarDelay = None
            if _crntData["isAudio"] and _audioPath:
                _audioPath = _audioPath.path
                # avatar audio present
                _avatarDelay = _crntData["avatarStartTime"]
                stayTime = _crntData["avatarStayTime"]
                avatarEndTime = round(_avatarDelay+stayTime,2)

                _avatarAudioClip = AudioFileClip(_audioPath)
                _newStayTime = _sceneInst.avatarTotalTime
                _changeInStayTime = _newStayTime - stayTime

                if _changeInStayTime>0.03 or _changeInStayTime<0.03:
                    for _vid in _allVideo:
                        if round(_vid["stayTime"]+_vid["enterDelay"],2) == avatarEndTime:
                            _vid["stayTime"] += _changeInStayTime

                    # change video clip duration if end time same and background
                    if avatarEndTime+_changeInStayTime>totalSceneDuration:
                        # increase background video duration
                        totalSceneDuration = avatarEndTime+_changeInStayTime
                        for _vid in _allVideo:
                            _typ = _vid.get("_Type",None)
                            if round(_vid["stayTime"]+_vid["enterDelay"],2) == totalSceneDuration and round(_vid["stayTime"]+_vid["enterDelay"],2) != avatarEndTime:
                                _vid["stayTime"] = totalSceneDuration
            
            crntAudioClip = AudioClip(lambda t: 0, duration=totalSceneDuration)
            allAudioClip = [crntAudioClip]
            # add current scene music
            _musicInfo = _crntData["musicInfo"]["currentScene"]
            for _smusicId in _musicInfo:
                try:
                    _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                    _crntMusicAudioClip = AudioFileClip(_minst.media_file.path)
                    # set volume
                    _vlm = convertFloat(_musicInfo[_smusicId]["volume"],1)
                    _volume = 1 if _vlm>10 else _vlm
                    _crntMusicAudioClip = volumex(_crntMusicAudioClip,_volume)
                    ## trim music 
                    _trimStart = convertFloat(_musicInfo[_smusicId]["trimStart"],0)
                    _trimEnd = convertFloat(_musicInfo[_smusicId]["trimEnd"],_crntMusicAudioClip.duration)
                    _trimStart = _trimStart if _trimStart<_trimEnd else 0
                    _crntMusicClip = audio_loop(_crntMusicAudioClip.subclip(_trimStart,_trimEnd),duration=totalSceneDuration)
                    allAudioClip.append(_crntMusicClip)
                except:
                    # file not found
                    pass

            # add video audio
            for _vidD in _allVideo:
                _vId = _vidD["id"]
                try:
                    _vidInst = APISaveVideo.objects.get(id=_vId)
                    if _vidInst.audio:
                        _crntMusicAudioClip = AudioFileClip(_vidInst.audio.path)
                        # set volume
                        _vlm = convertFloat(_vidD["volume"],1)
                        _volume = 1 if _vlm>10 else _vlm
                        _crntMusicAudioClip = volumex(_crntMusicAudioClip,_volume)

                        # trim music
                        _stayTime = convertFloat(_vidD["stayTime"],0)
                        _enterDelay = convertFloat(_vidD["enterDelay"],0)
                        _trimStart = convertFloat(_vidD["trimStart"],0)
                        _trimEnd = convertFloat(_vidD["trimEnd"],_crntMusicAudioClip.duration)
                        _trimStart = _trimStart if _trimStart<_trimEnd else 0
                        _crntMusicClip = _crntMusicAudioClip.subclip(_trimStart,_trimEnd)

                        # handle loop
                        if _vidD["adjustLength"] == 1 and _stayTime>0 and _enterDelay<totalSceneDuration:
                            _crntMusicClip = audio_loop(_crntMusicClip,duration=_stayTime)
                            allAudioClip.append(_crntMusicClip.set_start(_enterDelay))
                        # handle play rate
                        elif _vidD["adjustLength"] == 3:
                            _rate = round((totalSceneDuration/_crntMusicClip.duration),3)
                            _crntMusicClipM = _crntMusicClip.fl_time(lambda t:  _rate*t)
                            _crntMusicClipM.set_duration(_crntMusicClip.duration/_rate)
                            allAudioClip.append(_crntMusicClipM)
                        # freeze or only trim
                        else:
                            allAudioClip.append(_crntMusicClip.set_start(_enterDelay))
                except:
                    # file not found
                    pass
            
            # add avatar audio
            if _avatarAudioClip:
                _avatarDelay = convertFloat(_avatarDelay,0)
                allAudioClip.append(_avatarAudioClip.set_start(_avatarDelay))
            finalSceneAudio = CompositeAudioClip([*allAudioClip])
            finalAudioList.append(finalSceneAudio.subclip(0,totalSceneDuration))
            crntTotalDuration += totalSceneDuration

            for _crnId in _crntData["musicInfo"]["allScene"]:
                allSceneAudioData[_crnId] = _crntData["musicInfo"]["allScene"][_crnId]
        
        # combine all scene audio 
        finalAudioList = concatenate_audioclips(finalAudioList)
        finalAudio = [finalAudioList]
        ## handle all scene audio
        for _smusicId in allSceneAudioData:
            try:
                _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                _crntMusicAudioClip = AudioFileClip(_minst.media_file.path)
                # set volume
                _vlm = convertFloat(allSceneAudioData[_smusicId]["volume"],1)
                _volume = 1 if _vlm>10 else _vlm
                _crntMusicAudioClip = volumex(_crntMusicAudioClip,_volume)
                ## trim music 
                _trimStart = convertFloat(allSceneAudioData[_smusicId]["trimStart"],0)
                _trimEnd = convertFloat(allSceneAudioData[_smusicId]["trimEnd"],_crntMusicAudioClip.duration)
                if _trimStart<_trimEnd:
                    _crntMusicClip = audio_loop(_crntMusicAudioClip.subclip(_trimStart,_trimEnd),duration=crntTotalDuration)
                    finalAudio.append(_crntMusicClip)
            except:
                # file not found
                pass
        finalSceneAudio = CompositeAudioClip([*finalAudio])
        finalSceneAudio.write_audiofile(_videoGenInst.getSoundPath(),fps = 44100,bitrate="500k", ffmpeg_params=["-ar","44100","-ac", "2","-q:a", "0"])
        _videoGenInst.isSoundGenerated = True
        _videoGenInst.audio.name = _videoGenInst.getSoundName()
        _videoGenInst.save()
        _videoGenInst.updateProgress()
        return True
    except Exception as e:
        logger.error(f"Unable to Generate Music Exception: {e} Stack: {str(traceback.format_exc())}")
        open('../logs/MusicGenerator.error','a').write(f"Exception: {e} Stack: {str(traceback.format_exc())}\n")
        return False

from aiAudio.utils.loadAudioFile import pydubCombineAudio, pydubLoadFile,pydubBlankAudio
import math
def percentageToDB(_value):
    if _value>0:
        return 20*math.log(_value,10)
    return 20*math.log(0.01,10)

def generateAudioWithLibrosa(_videoGenId):
    try:
        _videoGenInst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoGenId)
        _parseData = json.loads(_videoGenInst.videoCreator.parseData)
        sceneIndex = _parseData["sceneArr"]
        
        sceneData = _parseData["data"]
        finalAudioList = []
        crntTotalDuration = 0

        allSceneAudioData = {}
        for _scId in sceneIndex:
            _sceneInst = _videoGenInst.aiSceneGenerate.get(sceneIndex=_scId)
            _audioPath = _sceneInst.avatarSound
            _crntData = sceneData[_scId]
            _allVideo = _crntData["musicInfo"]["video"].copy()
            totalSceneDuration = round(sceneData[_scId]["totalSceneDuration"],2)
            _avatarAudioClip = None
            _avatarDelay = None
            if _crntData["isAudio"] and _audioPath:
                _audioPath = _audioPath.path
                # avatar audio present
                _avatarDelay = _crntData["avatarStartTime"]
                stayTime = _crntData["avatarStayTime"]
                avatarEndTime = round(_avatarDelay+stayTime,2)

                _avatarAudioClip = pydubLoadFile(_audioPath)
                _newStayTime = _sceneInst.avatarTotalTime
                _changeInStayTime = _newStayTime - stayTime

                if _changeInStayTime>0.03 or _changeInStayTime<0.03:
                    for _vid in _allVideo:
                        if round(_vid["stayTime"]+_vid["enterDelay"],2) == avatarEndTime:
                            _vid["stayTime"] += _changeInStayTime

                    # change video clip duration if end time same and background
                    if avatarEndTime+_changeInStayTime>totalSceneDuration:
                        # increase background video duration
                        totalSceneDuration = avatarEndTime+_changeInStayTime
                        for _vid in _allVideo:
                            _typ = _vid.get("_Type",None)
                            if round(_vid["stayTime"]+_vid["enterDelay"],2) == totalSceneDuration and round(_vid["stayTime"]+_vid["enterDelay"],2) != avatarEndTime:
                                _vid["stayTime"] = totalSceneDuration
            
            crntAudioClip = pydubBlankAudio(totalSceneDuration)
            # add current scene music
            _musicInfo = _crntData["musicInfo"]["currentScene"]
            for _smusicId in _musicInfo:
                try:
                    _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                    _crntMusicAudioClip = pydubLoadFile(_minst.media_file.path)
                    # set volume
                    _vlm = convertFloat(_musicInfo[_smusicId]["volume"],1)
                    _volume = 1 if _vlm>10 else _vlm

                    ## trim music 
                    _trimStart = convertFloat(_musicInfo[_smusicId]["trimStart"],0)
                    _trimEnd = convertFloat(_musicInfo[_smusicId]["trimEnd"],_crntMusicAudioClip.duration_seconds)
                    _trimStart = _trimStart if _trimStart<_trimEnd else 0
                    _crntMusicClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]
                    crntAudioClip = crntAudioClip.overlay(_crntMusicClip,loop=True,gain_during_overlay=percentageToDB(_volume))
                except:
                    # file not found
                    pass

            # add video audio
            for _vidD in _allVideo:
                _vId = _vidD["id"]
                try:
                    _vidInst = APISaveVideo.objects.get(id=_vId)
                    if _vidInst.audio:
                        _crntMusicAudioClip = pydubLoadFile(_vidInst.audio.path)
                        # set volume
                        _vlm = convertFloat(_vidD["volume"],1)
                        _volume = 1 if _vlm>10 else _vlm

                        # trim music
                        _stayTime = convertFloat(_vidD["stayTime"],0)
                        _enterDelay = convertFloat(_vidD["enterDelay"],0)
                        _trimStart = convertFloat(_vidD["trimStart"],0)
                        _trimEnd = convertFloat(_vidD["trimEnd"],_crntMusicAudioClip.duration_seconds)
                        _trimStart = _trimStart if _trimStart<_trimEnd else 0
                        _crntMusicClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]

                        # handle loop
                        if _vidD["adjustLength"] == 1 and _stayTime>0 and _enterDelay<totalSceneDuration:
                            # handle later
                            crntAudioClip = crntAudioClip.overlay(_crntMusicClip,position=int(_enterDelay*1000),gain_during_overlay=percentageToDB(_volume))
                        # handle play rate
                        elif _vidD["adjustLength"] == 3:
                            # handle later
                            _rate = round((totalSceneDuration/_crntMusicClip.duration),3)
                            # _crntMusicClipM = _crntMusicClip.fl_time(lambda t:  _rate*t)
                            # _crntMusicClipM.set_duration(_crntMusicClip.duration/_rate)
                            # allAudioClip.append(_crntMusicClipM)
                        # freeze or only trim
                        else:
                            crntAudioClip = crntAudioClip.overlay(_crntMusicClip,position=int(_enterDelay*1000),gain_during_overlay=percentageToDB(_volume))
                except:
                    pass
            
            # add avatar audio
            if _avatarAudioClip:
                _avatarDelay = convertFloat(_avatarDelay,0)
                crntAudioClip = crntAudioClip.overlay(_avatarAudioClip,position=int(_avatarDelay*1000))

            crntAudioClip = crntAudioClip[0:int(totalSceneDuration*1000)]
            crntTotalDuration += totalSceneDuration
            finalAudioList.append(crntAudioClip)

            for _crnId in _crntData["musicInfo"]["allScene"]:
                allSceneAudioData[_crnId] = _crntData["musicInfo"]["allScene"][_crnId]
        
        finalAudioList = pydubCombineAudio(finalAudioList)
        for _smusicId in allSceneAudioData:
            try:
                _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                _crntMusicAudioClip = pydubLoadFile(_minst.media_file.path)

                _vlm = convertFloat(allSceneAudioData[_smusicId]["volume"],1)
                _volume = 1 if _vlm>10 else _vlm

                _trimStart = convertFloat(allSceneAudioData[_smusicId]["trimStart"],0)
                _trimEnd = convertFloat(allSceneAudioData[_smusicId]["trimEnd"],_crntMusicAudioClip.duration_seconds)
                if _trimStart<_trimEnd:
                    _crntMusicAudioClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]
                    finalAudioList = finalAudioList.overlay(_crntMusicAudioClip,loop=True,gain_during_overlay=percentageToDB(_volume))
            except:
                pass

        finalAudioList.export(_videoGenInst.getSoundPath(),parameters=["-ar","44100","-ac", "2","-q:a", "0"])
        _videoGenInst.isSoundGenerated = True
        _videoGenInst.audio.name = _videoGenInst.getSoundName()
        _videoGenInst.save()
        _videoGenInst.updateProgress()
        return True
    except Exception as e:
        logger.error(f"Unable to Generate Music Exception: {e} Stack: {str(traceback.format_exc())}")
        open('../logs/MusicGenerator.error','a').write(f"Exception: {e} Stack: {str(traceback.format_exc())}\n")
        return False



_ONE_FRAME_SEC = (1/settings.VIDEO_DEFAULT_FPS)
def generateAudio(_videoGenId):
    try:
        _videoGenInst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoGenId)
        _parseData = json.loads(_videoGenInst.videoCreator.parseData)
        sceneIndex = _parseData["sceneArr"]
        
        sceneData = _parseData["data"]
        finalAudioList = []
        _totalDuration = 0

        allSceneAudioData = {}
        # generate all Scene Music
        for _scId in sceneIndex:
            _crntData = sceneData[_scId]
            for _crnId in _crntData["musicInfo"]["allScene"]:
                allSceneAudioData[_crnId] = _crntData["musicInfo"]["allScene"][_crnId]
            _totalDuration += round(sceneData[_scId]["totalSceneDuration"]+_ONE_FRAME_SEC,2)
    
        finalAudioList = pydubBlankAudio(_totalDuration)
        for _smusicId in allSceneAudioData:
            try:
                _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                _crntMusicAudioClip = pydubLoadFile(_minst.media_file.path)

                _vlm = convertFloat(allSceneAudioData[_smusicId]["volume"],1)
                _volume = 1 if _vlm>10 else _vlm

                _trimStart = convertFloat(allSceneAudioData[_smusicId]["trimStart"],0)
                _trimEnd = convertFloat(allSceneAudioData[_smusicId]["trimEnd"],_crntMusicAudioClip.duration_seconds)
                if _trimStart<_trimEnd:
                    _crntMusicAudioClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]+percentageToDB(_volume)
                    finalAudioList = finalAudioList.overlay(_crntMusicAudioClip,loop=True)
            except:
                pass

        crntTotalDuration = 0
        for _scId in sceneIndex:
            _sceneInst = _videoGenInst.aiSceneGenerate.get(sceneIndex=_scId)
            _audioPath = _sceneInst.avatarSound
            _crntData = sceneData[_scId]
            _allVideo = _crntData["musicInfo"]["video"].copy()
            totalSceneDuration = round(sceneData[_scId]["totalSceneDuration"]+_ONE_FRAME_SEC,2)
            _avatarAudioClip = None
            _avatarDelay = None
            if _crntData["isAudio"] and _audioPath:
                _audioPath = _audioPath.path
                # avatar audio present
                _avatarDelay = _crntData["avatarStartTime"]
                stayTime = _crntData["avatarStayTime"]
                avatarEndTime = round(_avatarDelay+stayTime,2)

                _avatarAudioClip = pydubLoadFile(_audioPath)
                _newStayTime = _sceneInst.avatarTotalTime
                _changeInStayTime = _newStayTime - stayTime

                if _changeInStayTime>0.03 or _changeInStayTime<0.03:
                    for _vid in _allVideo:
                        if round(_vid["stayTime"]+_vid["enterDelay"],2) == avatarEndTime:
                            _vid["stayTime"] += _changeInStayTime

                    # change video clip duration if end time same and background
                    if avatarEndTime+_changeInStayTime>totalSceneDuration:
                        # increase background video duration
                        totalSceneDuration = avatarEndTime+_changeInStayTime
                        for _vid in _allVideo:
                            if round(_vid["stayTime"]+_vid["enterDelay"],2) == totalSceneDuration and round(_vid["stayTime"]+_vid["enterDelay"],2) != avatarEndTime:
                                _vid["stayTime"] = totalSceneDuration
            
            crntAudioClip = finalAudioList[crntTotalDuration: crntTotalDuration + int(totalSceneDuration*1000)] #pydubBlankAudio(totalSceneDuration)
            # add current scene music
            _musicInfo = _crntData["musicInfo"]["currentScene"]
            for _smusicId in _musicInfo:
                try:
                    _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                    _crntMusicAudioClip = pydubLoadFile(_minst.media_file.path)
                    # set volume
                    _vlm = convertFloat(_musicInfo[_smusicId]["volume"],1)
                    _volume = 1 if _vlm>10 else _vlm

                    ## trim music 
                    _trimStart = convertFloat(_musicInfo[_smusicId]["trimStart"],0)
                    _trimEnd = convertFloat(_musicInfo[_smusicId]["trimEnd"],_crntMusicAudioClip.duration_seconds)
                    _trimStart = _trimStart if _trimStart<_trimEnd else 0
                    _crntMusicClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]+percentageToDB(_volume)
                    crntAudioClip = crntAudioClip.overlay(_crntMusicClip,loop=True)
                except:
                    # file not found
                    pass

            # add video audio
            for _vidD in _allVideo:
                _vId = _vidD["id"]
                try:
                    _vidInst = APISaveVideo.objects.get(id=_vId)
                    if _vidInst.audio:
                        _crntMusicAudioClip = pydubLoadFile(_vidInst.audio.path)
                        # set volume
                        _vlm = convertFloat(_vidD["volume"],1)
                        _volume = 1 if _vlm>10 else _vlm

                        # trim music
                        _stayTime = convertFloat(_vidD["stayTime"],0)
                        _enterDelay = convertFloat(_vidD["enterDelay"],0)
                        _trimStart = convertFloat(_vidD["trimStart"],0)
                        _trimEnd = convertFloat(_vidD["trimEnd"],_crntMusicAudioClip.duration_seconds)
                        _trimStart = _trimStart if _trimStart<_trimEnd else 0
                        _crntMusicClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]+percentageToDB(_volume)

                        # handle loop
                        if _vidD["adjustLength"] == 1 and _stayTime>0 and _enterDelay<totalSceneDuration:
                            # handle later
                            crntAudioClip = crntAudioClip.overlay(_crntMusicClip,position=int(_enterDelay*1000))
                        # handle play rate
                        elif _vidD["adjustLength"] == 3:
                            # handle later
                            _rate = round((totalSceneDuration/_crntMusicClip.duration),3)
                            # _crntMusicClipM = _crntMusicClip.fl_time(lambda t:  _rate*t)
                            # _crntMusicClipM.set_duration(_crntMusicClip.duration/_rate)
                            # allAudioClip.append(_crntMusicClipM)
                        # freeze or only trim
                        else:
                            crntAudioClip = crntAudioClip.overlay(_crntMusicClip,position=int(_enterDelay*1000))
                except:
                    pass
            
            # add avatar audio
            if _avatarAudioClip:
                print(_avatarAudioClip.duration_seconds)
                _avatarDelay = convertFloat(_avatarDelay,0)
                crntAudioClip = crntAudioClip.overlay(_avatarAudioClip,position=int(_avatarDelay*1000))

            crntAudioClip = crntAudioClip[0:int(totalSceneDuration*1000)]
            crntTotalDuration += int(totalSceneDuration*1000)
            crntAudioClip.export(_sceneInst.getSceneAudioPath(),parameters=["-ar","44100","-ac", "2","-q:a", "0"])
            _sceneInst.isSceneAudioGenerated = True
            _sceneInst.sceneAudio.name = _sceneInst.getSceneAudioName()
            _sceneInst.save()
            _sceneInst.sendJobToVideoRender()
        _videoGenInst.isSoundGenerated = True
        _videoGenInst.save()
        _videoGenInst.updateProgress()
        return True
    except Exception as e:
        logger.error(f"Unable to Generate Music Exception: {e} Stack: {str(traceback.format_exc())}")
        open('../logs/MusicGenerator.error','a').write(f"Exception: {e} Stack: {str(traceback.format_exc())}\n")
        return False


def generateAudioWithSeprateMusic(_videoGenId):
    try:
        _videoGenInst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoGenId)
        _parseData = json.loads(_videoGenInst.videoCreator.parseData)
        sceneIndex = _parseData["sceneArr"]
        
        sceneData = _parseData["data"]
        finalAudioList = []
        _totalDuration = 0

        allSceneAudioData = {}
        # generate all Scene Music
        for _scId in sceneIndex:
            _crntData = sceneData[_scId]
            for _crnId in _crntData["musicInfo"]["allScene"]:
                allSceneAudioData[_crnId] = _crntData["musicInfo"]["allScene"][_crnId]
            _totalDuration += round(sceneData[_scId]["totalSceneDuration"]+_ONE_FRAME_SEC,2)
    
        finalAudioList = pydubBlankAudio(_totalDuration)
        _isMusicOverlay = False
        for _smusicId in allSceneAudioData:
            try:
                _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                _crntMusicAudioClip = pydubLoadFile(_minst.media_file.path)

                _vlm = convertFloat(allSceneAudioData[_smusicId]["volume"],1)
                _volume = 1 if _vlm>10 else _vlm

                _trimStart = convertFloat(allSceneAudioData[_smusicId]["trimStart"],0)
                _trimEnd = convertFloat(allSceneAudioData[_smusicId]["trimEnd"],_crntMusicAudioClip.duration_seconds)
                if _trimStart<_trimEnd:
                    _crntMusicAudioClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]+percentageToDB(_volume)
                    finalAudioList = finalAudioList.overlay(_crntMusicAudioClip,loop=True)
                    _isMusicOverlay = True
            except:
                pass

        if _isMusicOverlay:
            finalAudioList.export(_videoGenInst.getSoundPath(),parameters=["-ar","44100","-ac", "2","-q:a", "0"])
            _videoGenInst.audio.name = _videoGenInst.getSoundName()

        crntTotalDuration = 0
        for _scId in sceneIndex:
            _sceneInst = _videoGenInst.aiSceneGenerate.get(sceneIndex=_scId)
            _audioPath = _sceneInst.avatarSound
            _crntData = sceneData[_scId]
            _allVideo = _crntData["musicInfo"]["video"].copy()
            totalSceneDuration = round(sceneData[_scId]["totalSceneDuration"]+_ONE_FRAME_SEC,2)
            _avatarAudioClip = None
            _avatarDelay = None
            if _crntData["isAudio"] and _audioPath:
                _audioPath = _audioPath.path
                # avatar audio present
                _avatarDelay = _crntData["avatarStartTime"]
                stayTime = _crntData["avatarStayTime"]
                avatarEndTime = round(_avatarDelay+stayTime,2)

                _avatarAudioClip = pydubLoadFile(_audioPath)
                _newStayTime = _sceneInst.avatarTotalTime
                _changeInStayTime = _newStayTime - stayTime

                if _changeInStayTime>0.03 or _changeInStayTime<0.03:
                    for _vid in _allVideo:
                        if round(_vid["stayTime"]+_vid["enterDelay"],2) == avatarEndTime:
                            _vid["stayTime"] += _changeInStayTime

                    # change video clip duration if end time same and background
                    if avatarEndTime+_changeInStayTime>totalSceneDuration:
                        # increase background video duration
                        totalSceneDuration = avatarEndTime+_changeInStayTime
                        for _vid in _allVideo:
                            if round(_vid["stayTime"]+_vid["enterDelay"],2) == totalSceneDuration and round(_vid["stayTime"]+_vid["enterDelay"],2) != avatarEndTime:
                                _vid["stayTime"] = totalSceneDuration
            
            crntAudioClip = pydubBlankAudio(totalSceneDuration) #finalAudioList[crntTotalDuration: crntTotalDuration + int(totalSceneDuration*1000)] #pydubBlankAudio(totalSceneDuration)
            # add current scene music
            _musicInfo = _crntData["musicInfo"]["currentScene"]
            for _smusicId in _musicInfo:
                try:
                    _minst = userlibraryModels.FileUpload.objects.get(id=_smusicId)
                    _crntMusicAudioClip = pydubLoadFile(_minst.media_file.path)
                    # set volume
                    _vlm = convertFloat(_musicInfo[_smusicId]["volume"],1)
                    _volume = 1 if _vlm>10 else _vlm

                    ## trim music 
                    _trimStart = convertFloat(_musicInfo[_smusicId]["trimStart"],0)
                    _trimEnd = convertFloat(_musicInfo[_smusicId]["trimEnd"],_crntMusicAudioClip.duration_seconds)
                    _trimStart = _trimStart if _trimStart<_trimEnd else 0
                    _crntMusicClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]+percentageToDB(_volume)
                    crntAudioClip = crntAudioClip.overlay(_crntMusicClip,loop=True)
                except:
                    # file not found
                    pass

            # add video audio
            for _vidD in _allVideo:
                _vId = _vidD["id"]
                try:
                    _vidInst = APISaveVideo.objects.get(id=_vId)
                    if _vidInst.audio:
                        _crntMusicAudioClip = pydubLoadFile(_vidInst.audio.path)
                        # set volume
                        _vlm = convertFloat(_vidD["volume"],1)
                        _volume = 1 if _vlm>10 else _vlm

                        # trim music
                        _stayTime = convertFloat(_vidD["stayTime"],0)
                        _enterDelay = convertFloat(_vidD["enterDelay"],0)
                        _trimStart = convertFloat(_vidD["trimStart"],0)
                        _trimEnd = convertFloat(_vidD["trimEnd"],_crntMusicAudioClip.duration_seconds)
                        _trimStart = _trimStart if _trimStart<_trimEnd else 0
                        _crntMusicClip = _crntMusicAudioClip[int(_trimStart*1000):int(_trimEnd*1000)]+percentageToDB(_volume)

                        # handle loop
                        if _vidD["adjustLength"] == 1 and _stayTime>0 and _enterDelay<totalSceneDuration:
                            # handle later
                            crntAudioClip = crntAudioClip.overlay(_crntMusicClip,position=int(_enterDelay*1000))
                        # handle play rate
                        elif _vidD["adjustLength"] == 3:
                            # handle later
                            _rate = round((totalSceneDuration/_crntMusicClip.duration),3)
                            # _crntMusicClipM = _crntMusicClip.fl_time(lambda t:  _rate*t)
                            # _crntMusicClipM.set_duration(_crntMusicClip.duration/_rate)
                            # allAudioClip.append(_crntMusicClipM)
                        # freeze or only trim
                        else:
                            crntAudioClip = crntAudioClip.overlay(_crntMusicClip,position=int(_enterDelay*1000))
                except:
                    pass
            
            # add avatar audio
            if _avatarAudioClip:
                print(_avatarAudioClip.duration_seconds)
                _avatarDelay = convertFloat(_avatarDelay,0)
                crntAudioClip = crntAudioClip.overlay(_avatarAudioClip,position=int(_avatarDelay*1000))

            crntAudioClip = crntAudioClip[0:int(totalSceneDuration*1000)]
            crntTotalDuration += int(totalSceneDuration*1000)
            crntAudioClip.export(_sceneInst.getSceneAudioPath(),parameters=["-ar","44100","-ac", "2","-q:a", "0"])
            _sceneInst.isSceneAudioGenerated = True
            _sceneInst.sceneAudio.name = _sceneInst.getSceneAudioName()
            _sceneInst.save()
            _sceneInst.sendJobToVideoRender()
        _videoGenInst.isSoundGenerated = True
        _videoGenInst.save()
        _videoGenInst.updateProgress()
        return True
    except Exception as e:
        logger.error(f"Unable to Generate Music Exception: {e} Stack: {str(traceback.format_exc())}")
        open('../logs/MusicGenerator.error','a').write(f"Exception: {e} Stack: {str(traceback.format_exc())}\n")
        return False