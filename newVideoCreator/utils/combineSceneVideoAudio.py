import json,os
from django.conf import settings
from newVideoCreator import models as newVideoCreatorModels

from utils.common import executeCommand

def combineAudioVideo(_videoGenId):
    _videoGenInst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoGenId)
    _allSceneInst = _videoGenInst.aiSceneGenerate.all()
    #_sceneArr = json.loads(_videoGenInst.videoCreator.parseData)["sceneArr"]
    # create text file for video to combine
    _fileHandler = open(_videoGenInst.getCombineVideoTextPath(),'w')
    for _scInst in _allSceneInst:
        #_scInst = _videoGenInst.aiSceneGenerate.get(sceneIndex=int(_sceneIndex))
        _fileHandler.write(f"file '{_scInst.video.path}'\n")
    _fileHandler.close()
    _audioPath = _videoGenInst.audio
    _ffmpegCommand = None
    if _audioPath:
        _audioPath = _audioPath.path
        _ffmpegCommand = ["ffmpeg","-y",'-f','concat','-safe','0',"-i",_videoGenInst.getCombineVideoTextPath(),'-i', _audioPath,'-filter_complex',"[0:a][1:a]amerge=inputs=2[a]",'-map','0:v','-map',"[a]",'-c:v','copy','-c:a','aac','-strict','experimental','-b:a','192k','-ac', '2','-shortest',_videoGenInst.getVideoPath()]
    else:
        _ffmpegCommand = ["ffmpeg","-y",'-f','concat','-safe','0',"-i",_videoGenInst.getCombineVideoTextPath(),'-c','copy',_videoGenInst.getVideoPath()]

    _res = executeCommand(_ffmpegCommand)
    
    return _res


from multiprocessing import Pool
from threading import Thread

def combineVideoAtFileLevel(_videoGenId):
    _videoGenInst = newVideoCreatorModels.MainVideoGenerate.objects.get(id=_videoGenId)
    _allSceneInst = _videoGenInst.aiSceneGenerate.all()

    # create tmp directory
    _tmpP = f"/tmp/_vid-{_videoGenId}/"
    _videoConctList = "concat:"
    os.makedirs(_tmpP,exist_ok=True)
    _videoConvtCommand = []
    for _n,_scInst in enumerate(_allSceneInst):
        _tmpName = f"{_tmpP}{_n}.ts"
        _ffmpegCommand = ["ffmpeg","-y","-i",_scInst.video.path,"-c","copy","-bsf:v","h264_mp4toannexb","-f","mpegts", _tmpName]
        _videoConctList += _tmpName+"|"

        _crntThread = Thread(target=executeCommand,args=(_ffmpegCommand,))
        _crntThread.start()
        _videoConvtCommand.append(_crntThread)

    _videoConctList = _videoConctList[:-1]

    for _th in _videoConvtCommand:
        _th.join()
    # with Pool(5) as p:
    #     _res = p.map(executeCommand, _videoConvtCommand)


    _audioPath = _videoGenInst.audio
    _ffmpegCommand = None
    if _audioPath:
        _audioPath = _audioPath.path
        _ffmpegCommand = ["ffmpeg","-y","-i",_videoConctList,'-i', _audioPath,'-bsf:a','aac_adtstoasc','-filter_complex',"[0:a][1:a]amerge=inputs=2[a]",'-map','0:v','-map',"[a]",'-c:v','copy','-c:a','aac','-strict','experimental','-b:a','192k','-ac', '2','-shortest',_videoGenInst.getVideoPath()]
    else:
        _ffmpegCommand = ["ffmpeg","-y","-i",_videoConctList,'-c','copy','-bsf:a','aac_adtstoasc',_videoGenInst.getVideoPath()]
    
    with open('/home/govind/test/a.txt','a') as f:
        f.write(json.dumps(_ffmpegCommand)+'\n')

    _res = executeCommand(_ffmpegCommand)
    # executeCommand(['rm','-rf',_tmpP])
    # finish all video convert
    return _res

