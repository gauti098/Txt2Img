import cv2
import numpy as np
from skimage.filters import gaussian
import gizeh
import cv2


def createSquareMask(cornerRadius=50,squareSize=535,blur = 40,opacity=0.3):

    borderColor = (0,0,0)
    borderWidth = 0
    shadowPerc = 0.8
    remVv = squareSize*(1-shadowPerc)
    expectedCanvasSize = int(squareSize+remVv)

    position = (remVv/2,remVv/2)
    surface = gizeh.Surface(width=expectedCanvasSize,height=expectedCanvasSize,bg_color=(0,0,0))
    sqr = gizeh.square(l=squareSize, stroke=borderColor, stroke_width= borderWidth,xy=(position[0]+squareSize/2,position[1]+squareSize/2),fill=(1,1,1))

    sqr1 = gizeh.square(l=cornerRadius, stroke=borderColor, stroke_width= borderWidth,xy=(position[0]+cornerRadius/2,position[1]+cornerRadius/2),fill=(0,0,0))
    sarc1 = gizeh.circle(r=cornerRadius, stroke_width=borderWidth,stroke=(1,1,1),xy=(position[0]+cornerRadius,position[1]+cornerRadius),fill=(1,1,1))
    group1 = gizeh.Group([sqr1,sarc1])
    group3 = group1.rotate(np.pi).translate((squareSize+2*position[0],squareSize+2*position[1]))


    sqr2 = gizeh.square(l=cornerRadius, stroke=borderColor, stroke_width= borderWidth,xy=(position[0]+squareSize-cornerRadius/2,position[1]+cornerRadius/2),fill=(0,0,0))
    sarc2 = gizeh.circle(r=cornerRadius, stroke_width=borderWidth,stroke=(1,1,1),xy=(position[0]+squareSize-cornerRadius,position[1]+cornerRadius),fill=(1,1,1))
    group2 = gizeh.Group([sqr2,sarc2])
    group4 = group2.rotate(np.pi).translate((squareSize+2*position[0],squareSize+2*position[1]))

    sqr.draw(surface)
    group1.draw(surface)
    group2.draw(surface)
    group3.draw(surface)
    group4.draw(surface)

    
    blurMaskR = surface.get_npimage()
    im_gray = cv2.cvtColor(blurMaskR,cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(im_gray, thresh=80, maxval=255, type=cv2.THRESH_BINARY)
    mask = cv2.GaussianBlur(mask,(9,9),0)


    blurMask = cv2.add(np.uint8(gaussian(mask,sigma=blur)*(255*opacity)),mask).astype(float) / 255

    return blurMask,mask[int(position[1]):int(position[1])+squareSize,int(position[0]):int(position[0])+squareSize]/255,remVv//2,False


def createCircularMask(squareSize = 500,blur = 40,opacity=0.3):
    radius = squareSize/2
    shadowPerc = 0.75
    remVv = squareSize*(1-shadowPerc)
    w = int(squareSize+remVv)
    surface = gizeh.Surface(width=w, height=w)
    circle = gizeh.circle(r=radius, xy=[w/2,w/2], fill=(1,1,1))
    circle.draw(surface)

    blurMaskR = surface.get_npimage()
    im_gray = cv2.cvtColor(blurMaskR,cv2.COLOR_RGB2GRAY)
    mask = cv2.GaussianBlur(im_gray,(9,9),0)

    blurMask = cv2.add(np.uint8(gaussian(mask,sigma=blur)*(255*opacity)),mask).astype(float) / 255
    return blurMask,mask[int(remVv/2):int(remVv/2)+squareSize,int(remVv/2):int(remVv/2)+squareSize]/255,remVv//2,False


def createImageCircularMask(imgPath,squareSize = 500,blur = 40,opacity=0.3):

    radius = squareSize/2
    shadowPerc = 0.75
    remVv = squareSize*(1-shadowPerc)
    w = int(squareSize+remVv)
    surface = gizeh.Surface(width=w, height=w)
    circle = gizeh.circle(r=radius, xy=[w/2,w/2], fill=(1,1,1))
    circle.draw(surface)

    fullMask = cv2.GaussianBlur(cv2.cvtColor(surface.get_npimage(),cv2.COLOR_RGB2GRAY),(9,9),0)
    cropMask = fullMask[int(remVv/2):int(remVv/2)+squareSize,int(remVv/2):int(remVv/2)+squareSize] / 255
    blurMask = cv2.add(np.uint8(gaussian(fullMask,sigma=blur)*(255*opacity)),fullMask).astype(float) / 255
    
    personBackgroundImage = cv2.cvtColor(cv2.imread(imgPath), cv2.COLOR_BGR2RGB)
    prsBGH, prsBGW, _ = personBackgroundImage.shape
    prsNH,prsNW = blurMask.shape

    if prsBGH < prsNH:
        prsBS = prsNH/prsBGH
        personBackgroundImage = cv2.resize(personBackgroundImage,(0, 0), fx=prsBS, fy=prsBS)
    elif prsBGW < prsNW:
        prsBS = prsNW/prsBGW
        personBackgroundImage = cv2.resize(personBackgroundImage,(0, 0), fx=prsBS, fy=prsBS)

    prsBGH, prsBGW, _ = personBackgroundImage.shape
    personBackgroundImage = personBackgroundImage[int(prsBGH/2-prsNH/2):int(prsBGH/2-prsNH/2)+prsNH, int(prsBGW/2-prsNW/2):int(prsBGW/2-prsNW/2)+prsNW]
    
    fullMask = cv2.cvtColor(fullMask,cv2.COLOR_GRAY2RGB)/255
    prsBGBlur = gaussian(personBackgroundImage,sigma=blur)*255 
    personBackgroundImage = cv2.add(prsBGBlur*(1-fullMask),personBackgroundImage*fullMask)
    return blurMask,cropMask,remVv//2,personBackgroundImage

def createImageSquareMask(imgPath,cornerRadius=50,squareSize=535,blur = 40,opacity=0.3):

    borderColor = (0,0,0)
    borderWidth = 0
    shadowPerc = 0.8
    remVv = squareSize*(1-shadowPerc)
    expectedCanvasSize = int(squareSize+remVv)

    position = (remVv/2,remVv/2)
    surface = gizeh.Surface(width=expectedCanvasSize,height=expectedCanvasSize,bg_color=(0,0,0))
    sqr = gizeh.square(l=squareSize, stroke=borderColor, stroke_width= borderWidth,xy=(position[0]+squareSize/2,position[1]+squareSize/2),fill=(1,1,1))

    sqr1 = gizeh.square(l=cornerRadius, stroke=borderColor, stroke_width= borderWidth,xy=(position[0]+cornerRadius/2,position[1]+cornerRadius/2),fill=(0,0,0))
    sarc1 = gizeh.circle(r=cornerRadius, stroke_width=borderWidth,stroke=(1,1,1),xy=(position[0]+cornerRadius,position[1]+cornerRadius),fill=(1,1,1))
    group1 = gizeh.Group([sqr1,sarc1])
    group3 = group1.rotate(np.pi).translate((squareSize+2*position[0],squareSize+2*position[1]))


    sqr2 = gizeh.square(l=cornerRadius, stroke=borderColor, stroke_width= borderWidth,xy=(position[0]+squareSize-cornerRadius/2,position[1]+cornerRadius/2),fill=(0,0,0))
    sarc2 = gizeh.circle(r=cornerRadius, stroke_width=borderWidth,stroke=(1,1,1),xy=(position[0]+squareSize-cornerRadius,position[1]+cornerRadius),fill=(1,1,1))
    group2 = gizeh.Group([sqr2,sarc2])
    group4 = group2.rotate(np.pi).translate((squareSize+2*position[0],squareSize+2*position[1]))

    sqr.draw(surface)
    group1.draw(surface)
    group2.draw(surface)
    group3.draw(surface)
    group4.draw(surface)

    
    im_gray = cv2.cvtColor(surface.get_npimage(),cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(im_gray, thresh=80, maxval=255, type=cv2.THRESH_BINARY)
    fullMask = cv2.GaussianBlur(mask,(9,9),0)

    cropMask = fullMask[int(remVv/2):int(remVv/2)+squareSize,int(remVv/2):int(remVv/2)+squareSize] / 255
    blurMask = cv2.add(np.uint8(gaussian(fullMask,sigma=blur)*(255*opacity)),fullMask).astype(float) / 255
    
    personBackgroundImage = cv2.cvtColor(cv2.imread(imgPath), cv2.COLOR_BGR2RGB)
    prsBGH, prsBGW, _ = personBackgroundImage.shape
    prsNH,prsNW = blurMask.shape

    if prsBGH < prsNH:
        prsBS = prsNH/prsBGH
        personBackgroundImage = cv2.resize(personBackgroundImage,(0, 0), fx=prsBS, fy=prsBS)
    elif prsBGW < prsNW:
        prsBS = prsNW/prsBGW
        personBackgroundImage = cv2.resize(personBackgroundImage,(0, 0), fx=prsBS, fy=prsBS)

    prsBGH, prsBGW, _ = personBackgroundImage.shape
    personBackgroundImage = personBackgroundImage[int(prsBGH/2-prsNH/2):int(prsBGH/2-prsNH/2)+prsNH, int(prsBGW/2-prsNW/2):int(prsBGW/2-prsNW/2)+prsNW]
    
    fullMask = cv2.cvtColor(fullMask,cv2.COLOR_GRAY2RGB)/255
    prsBGBlur = gaussian(personBackgroundImage,sigma=blur)*255 
    personBackgroundImage = cv2.add(prsBGBlur*(1-fullMask),personBackgroundImage*fullMask)
    return blurMask,cropMask,remVv//2,personBackgroundImage