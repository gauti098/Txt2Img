import gizeh as gz
import cv2
from moviepy.editor import VideoClip
import numpy as np
from videoAutomation.config import MOVIEPY_CONFIG

def textAnimation1(videoClip,text_list,size,pos,fontsize=50,font='impact',interlineR = 0.3,transitionTime=1,textColor=(200,50,50),fps=30,bgAlpha=False,bgColor=(30,30,30,0.8)):
    textColor = (textColor[0]/255.0,textColor[1]/255.0,textColor[2]/255.0)
    bgColor = (bgColor[0]/255.0,bgColor[1]/255.0,bgColor[2]/255.0,bgColor[3])


    line_height = fontsize + interlineR * fontsize
    totalTextLen = len(text_list)

    bgClipDuration = videoClip.duration
    totalExtraTime =max(totalTextLen*transitionTime,bgClipDuration)
    #totalExtraTime = totalTextLen*transitionTime

    totalWidth=size[0]
    totalHeight=size[1]
    
    totalHeightC = line_height * totalTextLen
    if totalHeight<=totalHeightC:
        textStartPoint = (line_height//2)
    else:
        textStartPoint = (totalHeight - totalHeightC)//2

    startCirclePosX = fontsize*2
    startTextPosX = fontsize*2.6
    
    def makeTextFrame(t,bgColor=bgColor):
        surface = gz.Surface(totalWidth,totalHeight, bg_color=bgColor)
        noA = int(t/transitionTime)+1
        for n,ii in enumerate(text_list[:noA]):
            lineC = (n*line_height) + textStartPoint
            rf = gz.circle(r=(line_height//2)*interlineR, xy=(startCirclePosX, lineC), fill=textColor)
            rf.draw(surface)
            txt = gz.text(ii, fontfamily=font, fontsize=fontsize, fill=textColor,xy=(startTextPosX,lineC),h_align='left')
            txt.draw(surface)
        return surface.get_npimage(transparent=True)

    textInX = pos[0]
    textInY = pos[1]

    lastFrame = None

    #bgClipDuration = videoClip.duration

    def freeze_last_frame(t):
        global lastFrame
        if t < bgClipDuration:
            lastFrame = videoClip.get_frame(t)
        cdata = lastFrame.copy()
        textData = makeTextFrame(t)
        '''
        maskD = textData[:,:,3]
        textD = textData[:,:,:3]
        textWithMask = cv2.bitwise_and(textD,textD,mask = maskD)
        bgWithMask = cv2.bitwise_and(cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth],cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth],mask = cv2.bitwise_not(maskD))
        
        '''
        ## add alpha background
        maskD = textData[:,:,3]/255

        textDR = textData[:,:,0]*maskD
        textDG = textData[:,:,1]*maskD
        textDB = textData[:,:,2]*maskD
        
        maskDInverse = (1-maskD)
        textWithMask = cv2.merge((textDR,textDG,textDB))

        bgDR = cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth][:,:,0]*maskDInverse
        bgDG = cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth][:,:,1]*maskDInverse
        bgDB = cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth][:,:,2]*maskDInverse

        bgWithMask = cv2.merge((bgDR,bgDG,bgDB))
        #'''


        #ksize = (10, 10) 
        #bgWithMask = cv2.blur(bgWithMask, ksize)
        cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth] = np.add(bgWithMask,textWithMask)#cv2.bitwise_or(bgWithMask, textWithMask)
        return cdata

    return VideoClip(freeze_last_frame,duration=totalExtraTime).set_fps(fps)




def textAnimation1Back(videoClip,text_list,size,pos,fontsize=50,font='impact',interlineR = 0.3,transitionTime=1,textColor=(200,50,50),fps=30,bgAlpha=False,bgColor=(30,30,30,0.8)):
    textColor = (textColor[0]/255.0,textColor[1]/255.0,textColor[2]/255.0)
    bgColor = (bgColor[0]/255.0,bgColor[1]/255.0,bgColor[2]/255.0,bgColor[3])


    line_height = fontsize + interlineR * fontsize
    totalTextLen = len(text_list)

    bgClipDuration = videoClip.duration
    totalExtraTime =max(totalTextLen*transitionTime,bgClipDuration)

    totalWidth=size[0]
    totalHeight=size[1]
    
    totalHeightC = line_height * totalTextLen

    ## 5% person full height margin
    OW,OH = videoClip.size
    margin = int(OH*0.08)

    if totalHeight<=totalHeightC:
        textStartPoint = margin
    else:
        textStartPoint = (totalHeight - totalHeightC)//2


    textInX = int(textStartPoint-margin) + pos[0]
    textInY = pos[1]

    startCirclePosX = fontsize*2
    startTextPosX = fontsize*2.6


    totalHeight = int(totalHeightC + 2*margin)

    def makeTextFrame(t,bgColor=bgColor):
        surface = gz.Surface(totalWidth,totalHeight, bg_color=bgColor)
        noA = int(t/transitionTime)+1
        for n,ii in enumerate(text_list[:noA]):
            lineC = (n*line_height) + margin + line_height//2
            if ii:
                rf = gz.circle(r=(line_height//2)*interlineR, xy=(startCirclePosX, lineC), fill=textColor)
                rf.draw(surface)
            txt = gz.text(ii, fontfamily=font, fontsize=fontsize, fill=textColor,xy=(startTextPosX,lineC),h_align='left')
            txt.draw(surface)
        return surface.get_npimage(transparent=True)

    

    lastFrame = None

    

    def freeze_last_frame(t):
        global lastFrame
        if t < bgClipDuration:
            lastFrame = videoClip.get_frame(t)
        cdata = lastFrame.copy()
        textData = makeTextFrame(t)
        '''
        maskD = textData[:,:,3]
        textD = textData[:,:,:3]
        textWithMask = cv2.bitwise_and(textD,textD,mask = maskD)
        bgWithMask = cv2.bitwise_and(cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth],cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth],mask = cv2.bitwise_not(maskD))
        
        '''
        ## add alpha background
        maskD = textData[:,:,3]/255

        textDR = textData[:,:,0]*maskD
        textDG = textData[:,:,1]*maskD
        textDB = textData[:,:,2]*maskD
        
        maskDInverse = (1-maskD)
        textWithMask = cv2.merge((textDR,textDG,textDB))

        bgDR = cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth][:,:,0]*maskDInverse
        bgDG = cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth][:,:,1]*maskDInverse
        bgDB = cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth][:,:,2]*maskDInverse

        bgWithMask = cv2.merge((bgDR,bgDG,bgDB))
        #'''


        #ksize = (10, 10) 
        #bgWithMask = cv2.blur(bgWithMask, ksize)
        cdata[textInX:textInX+totalHeight,textInY:textInY+totalWidth] = np.add(bgWithMask,textWithMask)#cv2.bitwise_or(bgWithMask, textWithMask)
        return cdata

    return VideoClip(freeze_last_frame,duration=totalExtraTime).set_fps(fps)