from django.db import models
from django.contrib.auth import get_user_model
import json,re
from django.conf import settings
import os
from uuid import UUID,uuid4,uuid1
from base64 import b64decode
from utils.avatarConfig import getAvatarCoordinate
from appAssets.models import AvatarImages

import shutil

import logging
import traceback
logger = logging.getLogger(__name__)



from aiQueueManager.rabbitMQSendJob import rabbitMQSendJob


THUMBNAIL_CATEGORY = (
    (0,'VIDEO_SCENE'),
    (1,'PUBLIC_TEMPLATE'),
    (2,'USER_CREATED'),
)


class ThumbnailBase64FileUrl(models.Model):
    # Custom fields
    thumbnailTemplate = models.ForeignKey("MainThumbnail", on_delete=models.CASCADE)
    mediaFile = models.FileField(upload_to='userlibrary/thumbnailCropImage/')

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def getMediaUrl(self):
        return f"{settings.BASE_URL}{self.mediaFile.url}"
    

class MainThumbnail(models.Model):
    # Custom fields
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    category = models.IntegerField(default= 0,choices=THUMBNAIL_CATEGORY)
    currentAvatar = models.IntegerField(default= 4,blank=True,null=True)

    thumbnailImage = models.ImageField(upload_to='videoThumbnail/',default="videoThumbnail/default.jpg",blank=True,null=True)

    jsonData = models.TextField(blank=True,null=True)
    userColors = models.CharField(max_length=200,null=True,blank=True)
    isPublic = models.BooleanField(default=False)
    isPersonalized = models.BooleanField(default=False)

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return f"{self.name} AvatarId: {self.currentAvatar}"

    def updateThumbnail(self):
        isValid,_jsonD = self.parseJsonData(self.jsonData)
        if isValid:
            outputPath = self.thumbnailImage.path
            uuidName = os.path.basename(outputPath)
            try:
                isValidUUid = UUID(uuidName.split('.')[0])
                isFound = os.path.isfile(outputPath)
                if isFound:
                    _oldPath = outputPath
                outputPath = outputPath.replace(uuidName,f"{uuid4()}.jpeg")
                if isFound:
                    try:
                        shutil.move(_oldPath,outputPath)
                    except:
                        pass
            except:
                outputPath = outputPath.replace(uuidName,f"{uuid4()}.jpeg")

            fabricData = {"jsonData": _jsonD,"outputPath": outputPath,"user": self.user.id,"id": self.id}
            rabbitMQSendJob('fabricJsonToImage',json.dumps(fabricData),durable=True)
            self.thumbnailImage = outputPath.split(settings.MEDIA_ROOT)[1]
            self.save()


    def replaceAvatar(self):
        allAvatars = AvatarImages.objects.all().exclude(id=4)
        for _avatarInst in allAvatars:
            _jsonData = json.loads(self.jsonData)
            _objects = _jsonData["objects"]
            for _object in _objects:
                try:
                    if _object["_Name"] == "Avatar":
                        # getAvatarCoordinate(prsCategory, prsPosition, avatarConfig)
                        # scale(getCords.scale * scaleBy).set({ left: getCords.ax * scaleBy, top: getCords.ay * scaleBy });
                        if self.name in ["Template 1","Template 2","Template 3","Template 4"]:
                            # change Avatar Full (Postion 2)
                            _avatarConfig = json.loads(_avatarInst.avatarConfig)
                            _getCords = getAvatarCoordinate(0,2,_avatarConfig)
                            _object["src"] = settings.BASE_URL + _avatarInst.transparentImage.url
                            _object["scaleX"] = _getCords["scale"]
                            _object["scaleY"] = _getCords["scale"]
                            _object["left"] = _getCords["ax"]
                            _object["top"] = _getCords["ay"]
                        elif self.name in ["Template 5"]:
                            _avatarConfig = json.loads(_avatarInst.avatarConfig)
                            _getCords = getAvatarCoordinate(0,0,_avatarConfig)
                            _object["src"] = settings.BASE_URL + _avatarInst.transparentImage.url
                            _object["scaleX"] = _getCords["scale"]
                            _object["scaleY"] = _getCords["scale"]
                            _object["left"] = _getCords["ax"]
                            _object["top"] = _getCords["ay"]
                        elif self.name in ["Template 8","Template 6"]:
                            # circle bottom right
                            _avatarConfig = json.loads(_avatarInst.avatarConfig)
                            _getCords = getAvatarCoordinate(2,5,_avatarConfig)
                            getClipSize = _getCords["size"] / 2
                            getClipCenterX = (_getCords["x"] + getClipSize)
                            getClipCenterY = (_getCords["y"] + getClipSize)
                            avatarOriginX = ((_getCords["x"] - _getCords["ax"]) + _getCords["size"] / 2) / (1080 * _getCords["scale"])
                            avatarOriginY = ((_getCords["y"] - _getCords["ay"]) + _getCords["size"] / 2) / (1920 * _getCords["scale"])
                            _object["src"] = settings.BASE_URL + _avatarInst.transparentImage.url
                            _object["scaleX"] = _getCords["scale"]
                            _object["scaleY"] = _getCords["scale"]
                            _object["left"] = getClipCenterX
                            _object["top"] = getClipCenterY
                            _object["originX"] = avatarOriginX
                            _object["originY"] = avatarOriginY

                            # change clip path
                            _object["clipPath"]["left"] = -_object['width'] / 2 + (_getCords["x"] - _getCords["ax"]) / _getCords["scale"]
                            _object["clipPath"]["top"] = -_object['height'] / 2 + (_getCords["y"] - _getCords["ay"]) / _getCords["scale"]
                            _object["clipPath"]["radius"] = getClipSize / _getCords["scale"]
                        
                        elif self.name in ["Template 7"]:
                            # square center right
                            _avatarConfig = json.loads(_avatarInst.avatarConfig)
                            _getCords = getAvatarCoordinate(1,2,_avatarConfig)
                            getClipSize = _getCords["size"] / 2
                            getClipCenterX = (_getCords["x"] + getClipSize)
                            getClipCenterY = (_getCords["y"] + getClipSize)
                            avatarOriginX = ((_getCords["x"] - _getCords["ax"]) + _getCords["size"] / 2) / (1080 * _getCords["scale"])
                            avatarOriginY = ((_getCords["y"] - _getCords["ay"]) + _getCords["size"] / 2) / (1920 * _getCords["scale"])
                            _object["src"] = settings.BASE_URL + _avatarInst.transparentImage.url
                            _object["scaleX"] = _getCords["scale"]
                            _object["scaleY"] = _getCords["scale"]
                            _object["left"] = getClipCenterX
                            _object["top"] = getClipCenterY
                            _object["originX"] = avatarOriginX
                            _object["originY"] = avatarOriginY

                            # change clip path
                            _object["clipPath"]["left"] = -_object['width'] / 2 + (_getCords["x"] - _getCords["ax"]) / _getCords["scale"]
                            _object["clipPath"]["top"] = -_object['height'] / 2 + (_getCords["y"] - _getCords["ay"]) / _getCords["scale"]
                            _object["clipPath"]["width"] =  _getCords["size"] / _getCords["scale"]
                            _object["clipPath"]["height"] =  _getCords["size"] / _getCords["scale"]
                            _object["clipPath"]["rx"] =  _object["clipPath"]["width"] * 0.09
                            _object["clipPath"]["ry"] =  _object["clipPath"]["height"]  * 0.09
                        

                except Exception as e:
                    print("Error: thumbnail set: ",e,str(traceback.format_exc()))
            _jsonData = json.dumps(_jsonData)
            _newInst,ct = MainThumbnail.objects.get_or_create(name=self.name,user=self.user,category=self.category,currentAvatar=_avatarInst.id,jsonData=_jsonData,isPublic=self.isPublic)
            _newInst.updateThumbnail()

    def replaceBase64ImageToFile(self):
        _jsonData = json.loads(self.jsonData)
        _objects = _jsonData["objects"]
        isChanged = False
        for _object in _objects:
            if _object["type"] == "image":
                _src = _object.get("src",None)
                if _src:
                    try:
                        if _src[:10] == "data:image":
                            ## base64 image
                            _imageType = _src.split('base64')[0].split('image')[1].strip().replace('/','').replace(';','').strip()
                            _base64Data = b64decode(_src.split('base64,')[1].strip())
                            _fileRootDir = "userlibrary/thumbnailCropImage/"
                            _fileN = f"{uuid4()}.{_imageType}"
                            _fileFolders = os.path.join(settings.BASE_DIR,settings.MEDIA_ROOT,_fileRootDir)
                            os.makedirs(_fileFolders,exist_ok=True)
                            _fileName = os.path.join(_fileFolders,_fileN)
                            with open(_fileName,"wb") as f:
                                f.write(_base64Data)
                            _fileInst = ThumbnailBase64FileUrl(thumbnailTemplate=self)
                            _fileInst.mediaFile.name = _fileRootDir + _fileN
                            _fileInst.save()
                            mediaUrl = _fileInst.getMediaUrl()
                            _object["src"] = mediaUrl
                            isChanged = True
                    except:
                        logger.error(str(traceback.format_exc()))
        if isChanged:
            self.jsonData = json.dumps(_jsonData)
            self.save()

        


    def getMergeTag(self):
        try:
            allMergeTag = []
            _thumbnailData = json.loads(self.jsonData)
            ## parse text mergeTag
            _objects =  _thumbnailData["objects"]#_thumbnailData["canvas"]["objects"]
            for _object in _objects:
                ## parse i text mergetag
                if _object["type"] == "i-text" or _object["type"] == "textbox":
                    try:
                        _textData = _object["text"]
                        _allTagFound = ['{{'+ i+ '}}' for i in re.findall(settings.MERGE_TAG_PATTERN, _textData)]
                        allMergeTag.extend(_allTagFound)
                    except Exception as e:
                        print('Error in Getting MergeTag from Thumbnail: ',e)
                        #open("../data",'w').write('hey: '+str(e))
                else:
                    try:
                        _objType = _object.get("_Type",None)
                        _objIsM = _object.get("_Merge",None)

                        if _objType == "Website":
                            if _objIsM:
                                allMergeTag.append("{{WebsiteScreenshot}}")
                        if _objType == "Logo":
                            if _objIsM:
                                allMergeTag.append("{{Logo}}")
                        if _objType == "Profile":
                            if _objIsM:
                                allMergeTag.append("{{Profile}}")
                        
                    except:
                        pass
            _backgroundImage = _thumbnailData.get("backgroundImage",None)
            if _backgroundImage !=None:
                try:
                    _objType = _backgroundImage.get("_Type",None)
                    _objIsM = _backgroundImage.get("_Merge",None)
                    if _objIsM:
                        if _objType == "Website":
                            allMergeTag.append("{{WebsiteScreenshot}}")
                        if _objType == "Logo":
                            allMergeTag.append("{{Logo}}")
                        if _objType == "Profile":
                            allMergeTag.append("{{Profile}}")
                except:
                    pass
                
            return allMergeTag
        except Exception as e:
            print('Error in Getting MergeTag from Thumbnail: ',e)
            #open("../data",'w').write('hey1: '+str(e))
            return []

    def getDefaultData(self):
        data = '{"version":"4.5.1","objects":[],"background":"#ffffff"}'
        return data

    def parseJsonData(self,data):
        try:
            parseData = json.loads(data)
            return True,parseData#['canvas']
        except:
            return False,None

    def getParseFabricJsonData(self,mergeTag):
        try:
            parseData = json.loads(self.jsonData)
            _objects = parseData["objects"]#parseData["canvas"]["objects"]
            for _object in _objects:
                ## parse i text mergetag
                if _object["type"] == "i-text" or _object["type"] == "textbox":
                    try:
                        _textData = _object["text"]
                        for _reMatch in re.finditer(settings.MERGE_TAG_PATTERN, _textData):
                            _mstartIndex = _reMatch.start()
                            _mendIndex = _reMatch.end()
                            _curntTag = _textData[_mstartIndex:_mendIndex]
                            _getMValue = mergeTag.get(_curntTag,None)
                            if _getMValue:
                                _object["text"] = _object["text"][:_mstartIndex] +_getMValue + _object["text"][_mendIndex:]
                                _netValueLength = len(_getMValue)

                                _textWithLines = _object["text"][:_mstartIndex].split('\n')
                                _currentLineIndex = len(_textWithLines) - 1

                                ## calculate previous padding
                                _totalStartPadding = 0
                                for ii in range(_currentLineIndex):
                                    _totalStartPadding+=len(_textWithLines[ii]) + 1
                                
                                
                                _mstartIndex -= _totalStartPadding
                                _mendIndex -= _totalStartPadding
                                
                                try:
                                    _currentStyles = _object["styles"].get(str(_currentLineIndex),None)
                                    if _currentStyles!=None:
                                        allKeysS = sorted([int(ii) for ii in list(_currentStyles.keys())])
                                        _diffInLength = _netValueLength - len(_curntTag)
                                        allUsefulStyles = {ii: 0 for ii in range(_mstartIndex,_mendIndex)}
                                        for ii in allKeysS:
                                            if _mstartIndex<=ii<_mendIndex:
                                                allUsefulStyles[ii] = _currentStyles[str(ii)].copy()
                                            elif _mendIndex<=ii:
                                                _currentStyles[ii+_diffInLength] = _currentStyles[ii]
                                                _currentStyles.pop(ii,None)
                                        allUsefulStyles = list(allUsefulStyles.values())
                                        for nn,ii in enumerate(range(_mstartIndex,_mstartIndex+_netValueLength)):
                                            _cst = allUsefulStyles[nn%len(allUsefulStyles)]
                                            if _cst!=0:
                                                _currentStyles[ii] = _cst

                                        _object["styles"][str(_currentLineIndex)]=_currentStyles
                                except:
                                    pass
                                _getTagStyes = _object

                    except:
                        pass
                else:
                    try:
                        _objType = _object.get("_Type",None)
                        _objIsM = _object.get("_Merge",None)

                        if _objType == "Website":
                            if _objIsM:
                                _getMValue = mergeTag.get("{{WebsiteScreenshot}}",None)
                                if _getMValue:
                                    _object["WebsiteScreenshot"] = _getMValue
                        if _objType == "Logo":
                            if _objIsM:
                                _getMValue = mergeTag.get("{{Logo}}",None)
                                if _getMValue:
                                    _object["src"] = _getMValue
                        if _objType == "Profile":
                            if _objIsM:
                                _getMValue = mergeTag.get("{{Profile}}",None)
                                if _getMValue:
                                    _object["src"] = _getMValue
                        
                    except:
                        pass
            _backgroundImage = parseData.get("backgroundImage",None)
            if _backgroundImage !=None:
                try:
                    _objType = _backgroundImage.get("_Type",None)
                    _objIsM = _backgroundImage.get("_Merge",None)
                    if _objIsM:
                        if _objType == "Website":
                            _getMValue = mergeTag.get("{{WebsiteScreenshot}}",None)
                            if _getMValue:
                                parseData["backgroundImage"]["WebsiteScreenshot"] = _getMValue
                except:
                    pass
            return True,parseData#['canvas']
        except Exception as e:
            logger.error(str(traceback.format_exc()))
            return False,None

