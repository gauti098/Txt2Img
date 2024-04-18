import time
import av
import sys

filename = sys.argv[1]


def checkIfAudioIsPresent(container):
    if len(container.streams.audio):
        return True
    return False

def extractFrames(container):
    for packet in container.demux():
        for frame in packet.decode():
            if frame.type == 'video':
                frame.to_image().save('/path/to/frame-%04d.jpg' % frame.index)



def getDemux(filename):
    container = av.open(filename)
    isAudio = checkIfAudioIsPresent(container)
    if isAudio:
        # extract audio to wav file
        pass

    #check if video is transparent
    crntVideoStream = container.streams.video[0]
    codexCtx = crntVideoStream.codec_context
    streamIndex = crntVideoStream.index
    crntVideoStream.thread_type = 'AUTO'
    allPacket = container.demux()
    allP = []
    for ii in allPacket:
        if ii.stream_index==streamIndex:
            mainData = {'offset': ii.pos,'size': ii.size,'keyframe': ii.is_keyframe}
            allP.append(mainData)
            print(f"Pos: {ii.pos} Size: {ii.size} Duration: {ii.duration} dts: {ii.dts} pts: {ii.pts} keyFrame: {ii.is_keyframe}")
    return allP


def extractTransparentFrames(videoName):
    videoName = "/home/govind/VideoAutomation/src/uploads/userlibrary/file/Ll03f0J7pwRdm4qC1yYPqgu0o2kgSxJz.webm"
    container = av.open(videoName)

    for packet in container.demux():
        for frame in packet.decode():
            try:
                frame.to_image().save('/home/govind/VideoAutomation/test/frame-%04d.webp' % frame.index)
            except:
                pass