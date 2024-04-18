import logging,math
import random
from pyunsplash import PyUnsplash
from django.conf import settings
logging.getLogger("pyunsplash").setLevel(logging.ERROR)

API_KEY = settings.UNSPLASH_API_KEY
PY_UNSPLASH_INST = PyUnsplash(api_key=API_KEY)


def getParseData(_data,addSource=True):
    finalData = []
    for _d in _data:
        try:
            _dd = _d.body
            _name = _dd["alt_description"]
            if not _name:
                _name = f'random-{random.randint(1,1000)}'
            if addSource:
                finalData.append({"name": _name,"low_url": _dd["urls"]["small"],"high_url": _dd["urls"]["raw"],"source": "unsplash"})
            else:
                finalData.append({"name": _name,"low_url": _dd["urls"]["small"],"high_url": _dd["urls"]["raw"]})
        except:
            pass
    return finalData

def getDefault(totalItem=100,addSource=True):
    MAX_PAGE = 30
    collections = PY_UNSPLASH_INST.photos(type_='generic', per_page=30)
    finalList = []

    for _ii in range(math.ceil(totalItem/MAX_PAGE)):
        finalList.extend(getParseData(collections.entries,addSource))
        if collections.has_next:
            collections = collections.get_next_page()

    return finalList

def getQuery(query,page=1,totalItem=30,addSource=False):
    MAX_PAGE = 30
    collections = PY_UNSPLASH_INST.search(type_='photos', query=query,page=page, per_page=30)
    finalList = []

    for _ii in range(math.ceil(totalItem/MAX_PAGE)):
        finalList.extend(getParseData(collections.entries,addSource))
        if collections.has_next:
            collections = collections.get_next_page()

    return finalList

