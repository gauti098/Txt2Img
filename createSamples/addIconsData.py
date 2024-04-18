from externalAssets.models import Icons
import os,pickle
import shutil
from django.conf import settings

rootP = settings.BASE_DIR
iconsPath = os.path.join(rootP,"uploads/externalAssets/icons/")

dataRootP = "/home/govind/test/icons/social-media-icons-5/"
data = pickle.load(open(os.path.join(dataRootP,"data.pkl"),"rb"))["details"]

for url in data:
    _md = data[url]
    _tags = f"{' '.join(_md['tags'])} {' '.join(_md['categories'])} {' '.join(_md['styles'])}"
    _filename = url.split('/')[-1] + ".svg"
    _nfilename = 'social-media-icons-5_'+url.split('/')[-1] + ".svg"
    shutil.copy(os.path.join(dataRootP,'images',_filename),os.path.join(iconsPath,_nfilename))
    srcName = "externalAssets/icons/" + _nfilename
    _inst = Icons(name=url.split('/')[-1],tags=_tags)
    _inst.src.name = srcName
    _inst.save()



