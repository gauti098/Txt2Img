from threading import Thread
import requests,json
import os
from uuid import uuid4
import time,json
from django.conf import settings
from utils.common import convertInt, executeCommand
from shutil import move

# from moviepy.editor import AudioFileClip,CompositeAudioClip,concatenate_audioclips,AudioClip
# from moviepy.audio.fx.all import volumex
from pydub import AudioSegment

def deleteClip(clipId,headers):
    url = "https://studio.wellsaidlabs.com/api/graphql"
    data = {
        "operationName":"DeleteClip",
        "variables":{"inputs":{"clipId":clipId}},
        "query":"mutation DeleteClip($inputs: DeleteClipInputs!) {\n  deleteClip(inputs: $inputs) {\n    code\n    success\n    message\n    clip {\n      id\n      isDeleted\n      __typename\n    }\n    wasReCredited\n    __typename\n  }\n}\n"
    }
    
    r = requests.post(url,data=json.dumps(data),headers=headers)

def headerFormat(cookies):
    headers = {
        'host': 'studio.wellsaidlabs.com', 
        'origin': 'https://studio.wellsaidlabs.com',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36', 
        'accept': 'application/json', 
        'accept-encoding': 'gzip, deflate, br', 
        'accept-language': 'en-US,en;q=0.9', 
        'connection': 'keep-alive', 
        'content-type': 'application/json', 
        'cookie': cookies,
    }
    return headers

def readCookies(path):
    _data = open(path,'r').read().split('\n')
    return {"isSuccess": int(_data[0]),"cookies": _data[1].strip(),"projectId": _data[2],"timestamp": int(_data[3])/1000}

def generateHeaders(forceUpdateToken = False,updateTime=3600):
    _isUpdateToken = forceUpdateToken
    _cookiesPath = "/home/govind/VideoAutomation/newVideoRender/wellSaidAutomations/wellSaidCookies.json"
    if not os.path.exists(_cookiesPath):
        _isUpdateToken = True
    if _isUpdateToken:
        os.system('node /home/govind/VideoAutomation/newVideoRender/wellSaidAutomations/index.js')
    _data = readCookies(_cookiesPath)
    if _data["isSuccess"]:
        if time.time()-_data["timestamp"]>updateTime:
            os.system('node /home/govind/VideoAutomation/newVideoRender/wellSaidAutomations/index.js')
            _data = readCookies(_cookiesPath)
    else:
        os.system('node /home/govind/VideoAutomation/newVideoRender/wellSaidAutomations/index.js')
        _data = readCookies(_cookiesPath)
        _cookies = _data.get("cookies",None)
        if _cookies:
            _headers = headerFormat(_cookies)
            return (True,{'headers': _headers,"projectId": _data.get("projectId",None)})
        else:
            return (False,None)
    if _data["isSuccess"]:
        _cookies = _data.get("cookies",None)
        if _cookies:
            _headers = headerFormat(_cookies)
            return (True,{'headers': _headers,"projectId": _data.get("projectId",None)})
        else:
            return (False,None)
    else:
        return (False,None)




def setAudioConf(_crnFile,outputFile,config={}):
    _speakerId = convertInt(config.get("speaker_id",None),None)
    if _speakerId==12:
        _res = executeCommand(['ffmpeg', '-y','-i', _crnFile,'-filter:a','loudnorm','-b:a','192k', outputFile])
    elif _speakerId == 3:
        _res = executeCommand(['ffmpeg', '-y','-i', _crnFile,'-filter:a',"atempo=1.15",'-b:a','192k', outputFile])
    else:
        move(_crnFile,outputFile)
    return True
    


'''{
            "projectId":"122793b1-951d-446b-85d0-311e07ed0cc6",
            "text":text,
            "speaker_id":"12",
            "speaker_variant_id":"12",
            "version":"latest"
        }
        '''

def generateSound(text,config,outFilePath,retry=2):
    try:
        _cacheDir = os.path.join(settings.BASE_DIR,'externalApi/wellsaid/_cache/')
        os.makedirs(_cacheDir,exist_ok=True)
        _forceUpdate = False
        for _index in range(retry):
            if _index!=0:
                _forceUpdate = True
            isSuccess,_headers = generateHeaders(_forceUpdate)
            if isSuccess:
                _newConfig = config.copy()
                _newConfig["text"] = text
                _newConfig["projectId"] = _headers["projectId"]
                _newConfig["version"] = config.get('version',"v9")

                apiUrl = 'https://studio.wellsaidlabs.com/api/v1/text_to_speech/stream'
                r = requests.post(apiUrl,data=json.dumps(_newConfig),headers = _headers["headers"])
                if r.status_code == 200:
                    _crntFileName = os.path.join(_cacheDir,f'{uuid4()}.mp3')
                    open(_crntFileName,"wb").write(r.content)
                    setAudioConf(_crntFileName,outFilePath,_newConfig)
                    clipId = r.headers['X-Clip-ID']
                    _th = Thread(target=deleteClip,args=(clipId,_headers["headers"],))
                    _th.start()
                    return True   
                else:
                    print(r.status_code,r.content)
    except Exception as e:
        open('/home/govind/data.l','a').write(f'{e}\n')
    return False

