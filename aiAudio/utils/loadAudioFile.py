from pydub import AudioSegment
import os,tempfile
from uuid import uuid4

from utils.common import executeCommand
from shutil import copy

def convertMp3AudioToWav(audioData):
    _inputP = audioData["inputPath"]
    _outputP = audioData["outputPath"]
    _ffmpegCommand = ["ffmpeg","-y","-i",_inputP,_outputP]
    _res = executeCommand(_ffmpegCommand)
    return True


def pydubLoadFile(filePath):
    return AudioSegment.from_file(filePath)

def pydubBlankAudio(sec):
    return AudioSegment.silent(duration=int(sec*1000))

def pydubCombineAudio(audioList):
    _finalAudio = AudioSegment.empty()
    for _audio in audioList:
        _finalAudio+=_audio
    return _finalAudio

def pydubCombineAudioFile(audioLists,outFile):
    _combineFileName = os.path.join(tempfile.mkdtemp(), f"{uuid4()}.txt")
    _fileList = open(_combineFileName,'w')
    for _fileD in audioLists:
        _type = _fileD.get("type",None)
        if _type == 'blank':
            _delay = _fileD.get("duration",None)
            _pyDub = pydubBlankAudio(_delay)
            _path = os.path.join(tempfile.mkdtemp(), f"{uuid4()}.mp3")
            _pyDub.export(_path, parameters=["-ar","44100","-ac", "2","-q:a", "0"])
            _fileList.write(f"file '{_path}'\n")
        elif _type == 'file':
            _path = _fileD.get('path',None)
            if _path:
                # _pyDub = pydubLoadFile(_path)
                # _pyDub.export(_path, parameters=["-ar","44100","-ac", "2","-q:a", "0"])
                _fileList.write(f"file '{_path}'\n")
    _fileList.close()
    _ffmpegCommand = ["ffmpeg","-y",'-f','concat','-safe','0',"-i",_combineFileName,"-ar","44100","-ac", "2","-q:a", "0",outFile] #'-c','copy',outFile]#"-ar","44100","-ac", "2","-b:a","192k","-q:a", "0",outFile]
    _res = executeCommand(_ffmpegCommand)
    return _res
