import subprocess
from subprocess import check_output


def getDurations(filePath):
    out = check_output(['ffprobe','-v', '0','-show_entries', "format=duration", "-of", 'compact=p=0:nk=1',f"{filePath}"])
    return float(out.decode().strip())

def removeAnimations(filePath,outputPath):
    _durations = getDurations(filePath)
    startTime = 0.4
    lastTime = _durations - 1.1
    ffmpegPipe = subprocess.Popen(['ffmpeg','-ss',str(startTime),'-i', filePath,'-to', str(lastTime),"-y",outputPath], stdin=subprocess.PIPE, stderr=subprocess.PIPE,shell=False)
    out, err = ffmpegPipe.communicate()
    if out:
        out = out.decode()
    if err:
        err = err.decode()
    return 0