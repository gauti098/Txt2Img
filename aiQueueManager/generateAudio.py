
from moviepy.editor import AudioFileClip,CompositeAudioClip,concatenate_audioclips,AudioClip
from moviepy.audio.fx.all import volumex,audio_loop
import os
from datetime import datetime
import traceback
from userlibrary.models import FileUpload

from aiQueueManager.models import GeneratedFinalVideo,AiTask

#mainData = {"type":"generateAudio","data":{"id":1091,"scenes":[{"id":509,"avatarStartFrame":12,"durations":2.03333},{"id":509,"avatarStartFrame":78,"durations":4.73333},{"id":509,"avatarStartFrame":159,"durations":8.33333},{"id":509,"avatarStartFrame":267,"durations":10.16666},{"id":509,"avatarStartFrame":322,"durations":12.39999}],"totalDurations":12.39999}}

def generateAudio(mainData):
    
    generatedFinalVideoInst = GeneratedFinalVideo.objects.get(id=mainData["id"])
    scenes = mainData["scenes"]
    try:
        outputPath = os.path.join(generatedFinalVideoInst.getcwd(),'sound.mp3')
        totalScene = generatedFinalVideoInst.multipleScene.singleScene.all()

        audioData = []
        aiAudioPath = None
        finalAiAudio = AudioClip(lambda t: 0, duration=mainData["totalDurations"])

        allAudioClip = [finalAiAudio]
        bgMusicTrack = {}
        _bgMusicT = {}

        for indx,currntScene in enumerate(totalScene):
            aiTaskId = scenes[indx]["id"]
            totalDurations = scenes[indx]["durations"]

            aiTaskInst = AiTask.objects.get(id = aiTaskId)
            try:
                if aiTaskInst.text.strip() == '' or currntScene.videoThemeTemplate.name == "No Avatar":
                    aiAudioPath = None
                else:
                    aiStartFrame = scenes[indx]["avatarStartFrame"]
                    aiAudioPath=os.path.join(aiTaskInst.getcwd(),'sound.wav')
                    allAudioClip.append(AudioFileClip(aiAudioPath).set_start(round(aiStartFrame/30,4)))
            except:
                pass

            isMusic = currntScene.isMusic
            musicPath = None
            if isMusic == 1:
                musicPath = FileUpload.objects.get(id=currntScene.music.id).media_file.path
                try:
                    previousBgMusic = AudioFileClip(musicPath)
                    previousBgMusic = volumex(previousBgMusic,0.2)

                    if indx==0:
                        bgMusicTrack[indx] = [previousBgMusic,0]
                    else:
                        bgMusicTrack[indx] = [previousBgMusic,scenes[indx-1]["durations"]]
                except:
                    pass

            _bgMusicT[indx] = {"isMusic": isMusic,"durations": totalDurations}

        allMusicStartP = sorted(list(bgMusicTrack.keys()))
        for musicIndex in range(len(allMusicStartP)):
            currentM = allMusicStartP[musicIndex]
            if len(allMusicStartP) == musicIndex+1:
                nextM = len(_bgMusicT)
            else:
                nextM = allMusicStartP[musicIndex+1]
            endDurations = 0
            for cmI in range(currentM,nextM):
                _tmpd = _bgMusicT[cmI]
                if _tmpd["isMusic"] == 1 or _tmpd["isMusic"] == -1:
                    endDurations = _tmpd["durations"]
                else:
                    break
            allAudioClip.append(audio_loop(bgMusicTrack[currentM][0], duration=endDurations - bgMusicTrack[currentM][1]).subclip(0,endDurations - bgMusicTrack[currentM][1]).set_start(bgMusicTrack[currentM][1]))
            
            
        finalAudio = CompositeAudioClip([*allAudioClip])
        finalAudio.write_audiofile(outputPath,fps = 44100)
        generatedFinalVideoInst.isSoundGenerated = True
        generatedFinalVideoInst.save()
        if generatedFinalVideoInst.combineAudioVideo():
            generatedFinalVideoInst.onVideoComplete()

    except:
        print(f"{datetime.now()}  == Final Audio Generation == {generatedFinalVideoInst.id} == {str(traceback.format_exc())}\n\n")
        open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Final Audio Generation == {generatedFinalVideoInst.id} == {str(traceback.format_exc())}\n\n")
    return 0
