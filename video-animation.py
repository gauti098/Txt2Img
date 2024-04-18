from moviepy.editor import *
from moviepy.video.tools.segmenting import findObjects 

from glob import glob

def create_single_scene_video(background_pth,bg_type,person_pos,category='full',fps=settings.VIDEO_DEFAULT_FPS):
    person_fixed = r'D:/Windows_installation/Documents/Python Tutorial/Python-Tut/sehaj/website/video-automation/videoAutomation/private_data/avatars/1/fullbody/without_swap/*.png'
    img_seq = sorted(glob(person_fixed))
    prsDuration = round(len(img_seq)/fps,2)
    if bg_type == 'video':
        background_clip = VideoFileClip(background_pth)
        bgW,bgH = background_clip.size
        
        #check generated video duration less than or equal to bg clip
        if prsDuration < background_clip.duration:
            background_clip = background_clip.subclip(t_end=prsDuration)
        elif prsDuration>background_clip.duration:
            background_clip=background_clip.fx(vfx.freeze,t='end',freeze_duration=prsDuration-background_clip.duration)

    elif bg_type == 'image':
        background_clip = ImageClip(background_pth).set_duration(prsDuration).set_fps(fps)
    else:
        return False

    if category == 'full':
        prsRatio = 3/4
        prsVideo = ImageSequenceClip(img_seq, fps=fps)
        prsW,prsH = prsVideo.size
        prsNH = int(prsRatio*bgH)
        prsScale = prsNH/prsH
        prsNW = int(prsScale*prsW)
        prsPadding = int(bgW*0.01)
        
        if person_pos == 'L':
            prsLeftPosition = (prsPadding,bgH-prsNH)
            prsVideo = prsVideo.set_duration(prsDuration).resize(prsScale).set_start(0).set_pos(prsLeftPosition)
        elif person_pos == 'R':
            prsRightPosition = (bgW-prsPadding-prsNW,bgH-prsNH)
            prsVideo = prsVideo.set_duration(prsDuration).resize(prsScale).set_start(0).set_pos(prsRightPosition)
        else:
            prsCenterPosition = (int(bgW/2-prsNW/2),bgH-prsNH)
            prsVideo = prsVideo.set_duration(prsDuration).resize(prsScale).set_start(0).set_pos(prsCenterPosition)
        return CompositeVideoClip([background_clip, prsVideo])
    else:
        ##person square
        personBackground = 'color' or 'image'
        personBackgroundColor = [255, 255, 100]
        person_fixed = r'D:/Windows_installation/Documents/Python Tutorial/Python-Tut/sehaj/website/video-automation/videoAutomation/private_data/avatars/1/square/without_swap/*.png'
        img_seq = sorted(glob(person_fixed))
        prsRatio = 1/3
        prsVideo = ImageSequenceClip(img_seq, fps=fps)
        prsW,prsH = prsVideo.size
        prsNH = int(prsRatio*bgH)
        prsScale = prsNH/prsH
        prsNW = int(prsScale*prsW)
        prsPadding = int(bgW*0.01)

        if person_pos == 'L':
            prsLeftPosition = (prsPadding,bgH-prsNH-prsPadding)
            prsVideo = prsVideo.set_duration(prsDuration).resize(prsScale).set_start(0).set_pos(prsLeftPosition)
        elif person_pos == 'R':
            prsRightPosition = (bgW-prsPadding-prsNW,bgH-prsNH-prsPadding)
            prsVideo = prsVideo.set_duration(prsDuration).resize(prsScale).set_start(0).set_pos(prsRightPosition)
        else:
            prsCenterPosition = (int(bgW/2-prsNW/2),bgH-prsNH-prsPadding)
            prsVideo = prsVideo.set_duration(prsDuration).resize(prsScale).set_start(0).set_pos(prsCenterPosition)

        if personBackground == 'color':
            personBackgroundclip = ColorClip(size =(prsNW, prsNH), color = personBackgroundColor).set_duration(prsDuration)
        else:
            personBackgroundclip = ImageClip(personBackgroundImage).set_duration(prsDuration).set_fps(fps)
        return CompositeVideoClip([background_clip, CompositeVideoClip([prsVideo,personBackgroundclip])])

video_p = r'D:/Windows_installation/Documents/Python Tutorial/Python-Tut/sehaj/website/video-automation/videoAutomation/uploads/images/api_videos/55_7ae0ea03-4ad1-4ab0-8271-1c7d87858e8f.mp4'
ret = create_single_scene_video(video_p,'image','R')
ret.write_videofile("myCustomRightImage.mp4")
