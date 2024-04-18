
def convertInt(val,default=0):
    tmp = val
    try:
        tmp = int(val)
    except:
        tmp = default
    return tmp

def convertFloat(val,default=0):
    tmp = val
    try:
        tmp = float(val)
    except:
        tmp = default
    return tmp

from django.conf import settings
import re
def getParsedText(text,onlyTag=False,mergeTag={}):
    allUsedMergeTag = list(set(["{{" + ii + "}}" for ii in re.findall(settings.MERGE_TAG_PATTERN,text)]))
    if onlyTag:
        return allUsedMergeTag

    for _tag in allUsedMergeTag:
        _tagVal = mergeTag.get(_tag,_tag[2:-2])
        text = text.replace(_tag,_tagVal)
    return text.strip()

import hashlib
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

import requests
def download_file(url,filePath,chunkSize=8192):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filePath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunkSize): 
                    f.write(chunk)
        return True
    except:
        return False

import cv2
def getVideoDuration(_videoPath):
    video = cv2.VideoCapture(_videoPath)
    frame = video.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = video.get(cv2.CAP_PROP_FPS)
    width  = video.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = video.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
   
    if fps>0:
        duration = round(frame/fps,2)
    else:
        duration = 0
    video.release()
    return {'duration': duration,'fps': fps,'frame': frame,"height": height,"width": width}

def getImageInfo(_imgP):
    try:
        img = cv2.imread(_imgP)
        _shape = img.shape
    except:
        _shape = (0,0,0)
    return {"height": _shape[0],"width": _shape[1]}


from itertools import cycle, islice

def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))

import subprocess
def executeCommand(command):
    ffmpegPipe = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE,shell=False)
    out, err = ffmpegPipe.communicate()
    if out:
        out = out.decode()
    if err:
        err = err.decode()
    return (out,err)

import av

def getWebmCodecName(filename):
    _codec = 'libvpx-vp9'
    try:
        container = av.open(filename)
        crntVideoStream = container.streams.video[0]
        codexCtxName = crntVideoStream.codec_context.name
        container.close()
        if codexCtxName=='vp8':
            _codec = 'libvpx'
        return _codec
    except:
        return _codec

import librosa
def getAudioDuration(audioPath):
    try:
        return round(librosa.get_duration(filename=audioPath),2)
    except:
        return 0