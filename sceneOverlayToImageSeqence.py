import os,subprocess

_folders = "/home/govind/VideoAutomation/src/uploads/newvideocreator/sceneoverlay/"
allFiles = os.listdir(_folders)

for _fileName in allFiles:
    _tmpF = os.path.join(_folders,_fileName.split('.')[0])
    _tmpFname = os.path.join(_folders,_fileName)
    os.system(f"rm -rf {_tmpF}")
    os.makedirs(_tmpF,exist_ok=True)

    ffmpegPipe = subprocess.Popen(['ffmpeg','-i', _tmpFname,'-vf', "fps=30","-start_number","0","-y",f"{_tmpF}/%05d.png"], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = ffmpegPipe.communicate()
    if out:
        out = out.decode()
    if err:
        err = err.decode()