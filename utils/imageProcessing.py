import cv2

def cropCenter(imgPath):
    tempImg = cv2.imread(imgPath)
    height,width,channels = tempImg.shape
    imgRatio = height/width
    orgRatio = 1080/1920
    bgScale = None
    if imgRatio<orgRatio:
        newHeight = 1080
        bgScale = 1080/height
        newWidth = int(width*bgScale)
        y1,y2 = (0,1080)
        remSize = int((newWidth - 1920)/2)
        x1,x2 = (remSize,remSize+1920)
    else:
        newWidth = 1920
        bgScale = 1920/width
        newHeight = int(height*bgScale)
        remSize = int((newHeight - 1080)/2)
        x1,x2 = (0,1920)
        y1,y2 = (remSize,remSize+1080)
    tempImg = cv2.resize(tempImg,(newWidth,newHeight))
    tempImg = tempImg[y1:y2,x1:x2]
    return tempImg