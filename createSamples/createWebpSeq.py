import cv2,os
from newVideoCreator.models import MainVideoGenerate

vidId = 3578
a = MainVideoGenerate.objects.get(videoCreator=vidId)
allSceneInfo = [[str(i.aiTask.uuid),i.aiTask.fullAudioPath.path] for i in a.aiSceneGenerate.all()]

workingDir = 'pmi'
rootDir = '/home/govind/VideoAutomation/src/uploads/newvideocreator/aiTask/'
workingFullDir = os.path.join(rootDir,workingDir)
os.makedirs(workingFullDir,exist_ok=True)
for n,scene in enumerate(allSceneInfo):
    os.system(f"cp -r {rootDir}imageSeq/{scene[0]}/ {rootDir}/{workingDir}/s{n}/")
    os.system(f"cp {scene[1]} {rootDir}/{workingDir}/s{n}.wav")


for n,scene in enumerate(allSceneInfo):
    _crntP = f"{rootDir}/{workingDir}/s{n}/"
    print('Processing: ',_crntP)
    allImgSeq = os.listdir(_crntP)
    for imgP in allImgSeq:
        imgFP = os.path.join(_crntP,imgP)
        im = cv2.imread(imgFP,-1)
        _ = cv2.imwrite(os.path.join(_crntP,imgP.replace('webp','png')),im)
        _ = os.remove(imgFP)


os.system(f"tar -czvf {rootDir}{workingDir}.tar.gz {rootDir}{workingDir}/")