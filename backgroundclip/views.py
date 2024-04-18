from datetime import date
import time
from aiQueueManager.models import VideoGradientColor
from externalApi.unsplash.fetchDefault import getDefault as unsplashPopularImages, getQuery as unsplashQueryImages
from userlibrary.serializers import FileUploadSerializer
from userlibrary.models import FileUpload
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
import numpy as np

import traceback
import logging
logger = logging.getLogger(__name__)


##my models
from backgroundclip.models import (
    APIImagePopularSaver, APIImageQuerySaver, APISaveImage, APISaveVideo, APIVideoPopularSaver, APIVideoQuerySaver, ImageSearch,ImageApiRes,
    VideoApiRes,VideoSearch,ApiQueryLogger
)
from backgroundclip.serializers import (
    APISaveImageSerializer,
    APISaveVideoSerializer,
    APIVideoSerializer,
    ImageApiResSerializer,
    VideoApiResSerializer,
    APIVideoPopularSerializer,
    APIImageSerializer,
    APIImagePopularSerializer,
    APISaveVideoServerSideSerializer
)
from utils.common import convertInt, download_file, roundrobin
from multiprocessing.pool import ThreadPool
import json
PEXELS_API_KEY = settings.PEXELS_API_KEY
PIXABAY_API_KEY = settings.PIXABAY_API_KEY


from pypexels import PyPexels
from pixabay import Image, Video

PIXABAY_IMAGE = Image(PIXABAY_API_KEY)
PIXABAY_VIDEO = Video(PIXABAY_API_KEY)

py_pexels = PyPexels(api_key=PEXELS_API_KEY)
per_page = 30


def processPixabayImage(results,addSource=False):
    allData = []
    for res in results['hits']:
        name = res['tags'].replace(', ',' ')
        high_res = res['fullHDURL']
        low_res = res['webformatURL']
        if addSource:
            allData.append({'name': name,'low_url': low_res,'high_url': high_res,"source": "pixabay"})
        else:
            allData.append({'name': name,'low_url': low_res,'high_url': high_res})
    return allData

def processPexelsImage(results,addSource=False):
    allData = []
    for res in results['photos']:
        org_img_url = res['src']['original']
        name = ' '.join(res['url'].split('photo/')[-1].split('-')[:-1])
        low_res = org_img_url+'?auto=compress&fit=crop&h=480'
        high_res = org_img_url
        if addSource:
            allData.append({'name': name,'low_url': low_res,'high_url': high_res,"source": "pexels"})
        else:
            allData.append({'name': name,'low_url': low_res,'high_url': high_res})
    return allData


def newAPIFetchImage(query,page,per_page=per_page):
    TOTAL_PROVIDER = 3
    CRNT_PAGE_START_INDEX = per_page*(page-1)*TOTAL_PROVIDER

    def pexels_image(query,page=1,QUERY_TTL=172800): #2*24*60*60
        PROVIDER = "pexels"
        _checker,ct = ApiQueryLogger.objects.get_or_create(query=query,page=page,providerName=PROVIDER,_type=0)
        if _checker.state==1:
            return 3

        _query = APIImageQuerySaver.objects.filter(_queryString=query,_page=page,_apiProvider=PROVIDER)
        if _query:
            _first = _query.first()
            _updatedDiff = timezone.now() - _first.timestamp
            if _updatedDiff.total_seconds()<QUERY_TTL:
                return 1
            else:
                _query = APIImageQuerySaver.objects.filter(_queryString=query,_apiProvider=PROVIDER)
                _query.delete()
                query = ApiQueryLogger.objects.get_or_create(query=query,providerName=PROVIDER,_type=0)
                query.delete()
                page = 1

        try:
            _checker.state = 1
            _checker.save()

            res_data = py_pexels.search(query=query,per_page=per_page,page=page)
            parseData = processPexelsImage(res_data.body)
            fdata = []
            for _n,_data in enumerate(parseData):
                _data["_queryString"] = query
                _data["_page"] = page
                _data["_apiProvider"] = PROVIDER
                _data["_order"] = CRNT_PAGE_START_INDEX + (_n*TOTAL_PROVIDER)
                fdata.append(APIImageQuerySaver(**_data))
   
            fdata = APIImageQuerySaver.objects.bulk_create(fdata)
            _checker.state = 2
            _checker.save()
            return 2
        except Exception as e:
            _checker.state = 0
            _checker.save()
            logger.error(f"newAPIFetchImage:pexels_image: {str(traceback.format_exc())}")
            return 0
        
    def pixabay_image(query,page=1,QUERY_TTL=86400): # 24*60*60
        PROVIDER = "pixabay"
        _checker,ct = ApiQueryLogger.objects.get_or_create(query=query,page=page,providerName=PROVIDER,_type=0)
        if _checker.state==1:
            return 3
        _query = APIImageQuerySaver.objects.filter(_queryString=query,_page=page,_apiProvider=PROVIDER)
        if _query:
            _first = _query.first()
            _updatedDiff = timezone.now() - _first.timestamp
            if _updatedDiff.total_seconds()<QUERY_TTL:
                return 1
            else:
                _query = APIImageQuerySaver.objects.filter(_queryString=query,_apiProvider=PROVIDER)
                _query.delete()
                query = ApiQueryLogger.objects.get_or_create(query=query,providerName=PROVIDER,_type=0)
                query.delete()
                page = 1

        try:
            _checker.state = 1
            _checker.save()
            res_data = PIXABAY_IMAGE.search(q=query,image_type='photo',order='latest',page=page,per_page=per_page)
            parseData = processPixabayImage(res_data)
            fdata = []
            
            for _n,_data in enumerate(parseData):
                _data["_queryString"] = query
                _data["_page"] = page
                _data["_apiProvider"] = PROVIDER
                _data["_order"] = CRNT_PAGE_START_INDEX + (_n*TOTAL_PROVIDER) + 1
                fdata.append(APIImageQuerySaver(**_data))
   
            fdata = APIImageQuerySaver.objects.bulk_create(fdata)
            _checker.state = 2
            _checker.save()
            return 2
        except Exception as e:
            _checker.state = 0
            _checker.save()
            logger.error(f"newAPIFetchImage:pixabay_image: {str(traceback.format_exc())}")
            return 0

    def unsplash_image(query,page=1,QUERY_TTL=172800): # 2*24*60*60
        PROVIDER = "unsplash"
        _checker,ct = ApiQueryLogger.objects.get_or_create(query=query,page=page,providerName=PROVIDER,_type=0)
        if _checker.state==1:
            return 3

        _query = APIImageQuerySaver.objects.filter(_queryString=query,_page=page,_apiProvider=PROVIDER)
        if _query:
            _first = _query.first()
            _updatedDiff = timezone.now() - _first.timestamp
            if _updatedDiff.total_seconds()<QUERY_TTL:
                return 1
            else:
                _query = APIImageQuerySaver.objects.filter(_queryString=query,_apiProvider=PROVIDER)
                _query.delete()
                query = ApiQueryLogger.objects.get_or_create(query=query,providerName=PROVIDER,_type=0)
                query.delete()
                page = 1

        try:
            _checker.state = 1
            _checker.save()
            fdata = []
            parseData = unsplashQueryImages(query,page=page)
            for _n,_data in enumerate(parseData):
                _data["_queryString"] = query
                _data["_page"] = page
                _data["_apiProvider"] = PROVIDER
                _data["_order"] = CRNT_PAGE_START_INDEX + (_n*TOTAL_PROVIDER) + 2
                fdata.append(APIImageQuerySaver(**_data))
   
            fdata = APIImageQuerySaver.objects.bulk_create(fdata)
            _checker.state = 2
            _checker.save()
            return 2
        except Exception as e:
            logger.error(f"newAPIFetchImage:unsplash_image: {str(traceback.format_exc())}")
            _checker.state = 0
            _checker.save()
            return 0
      

    pool = ThreadPool(TOTAL_PROVIDER)
    results = []
    results.append(pool.apply_async(pixabay_image, args=(query,page)))
    results.append(pool.apply_async(pexels_image, args=(query,page)))
    results.append(pool.apply_async(unsplash_image, args=(query,page)))
    pool.close()
    pool.join()
    results = [f"{r.get()}" for r in results]
    
    return " ".join(results)




def fetch_image(query,page,per_page=per_page):

    def pexels_image(query,page=1):
        inst, created = ImageSearch.objects.get_or_create(query_string=query,provider_name="pexels",provider_page=page)
        if not created:
            filter_query = ImageApiRes.objects.filter(query=inst)
            if filter_query:
                #serialize_data = ImageApiResSerializer(filter_query, many=True).data
                return filter_query
        fdata = []
        try:
            res_data = py_pexels.search(query=query,per_page=per_page,page=page,orientation="landscape")
            for res in res_data.body['photos']:
                org_img_url = res['src']['original']
                name = ' '.join(res['url'].split('photo/')[-1].split('-')[:-1])
                low_res = org_img_url+'?auto=compress&fit=crop&h=360&w=640'
                high_res = org_img_url+'?fit=crop&h=1080&w=1920'
                data = {'query': inst,'name': name,'low_url': low_res,'high_url': high_res}
                temp_inst = ImageApiRes(**data)
                fdata.append(temp_inst)
            
            fdata = ImageApiRes.objects.bulk_create(fdata)
        except Exception as e:
            print(e)
            fdata = []
        return ImageApiRes.objects.filter(query=inst)
    
    def pixabay_image(query,page=1):
        inst, created = ImageSearch.objects.get_or_create(query_string=query,provider_name="pixabay",provider_page=page)
        if not created:
            filter_query = ImageApiRes.objects.filter(query=inst)
            if query:
                #serialize_data = ImageApiResSerializer(filter_query, many=True).data
                return filter_query
        try:
            fdata = []
            res_data = PIXABAY_IMAGE.search(q=query,
                    image_type='photo',
                    orientation='horizontal',
                    order='latest',
                    min_width=1920,
                    min_height=1080,
                    page=page,
                    per_page=per_page)
            for res in res_data['hits']:
                name = res['tags']
                high_res = res['fullHDURL']
                low_res = res['webformatURL']
                data = {'query': inst,'name': name,'low_url': low_res,'high_url': high_res}
                temp_inst = ImageApiRes(**data)
                fdata.append(temp_inst)
            
            fdata = ImageApiRes.objects.bulk_create(fdata)
        except Exception as e:
            print(e)
            fdata = []
        return ImageApiRes.objects.filter(query=inst)

    pix_res = list(pixabay_image(query,page=page))
    pex_res = list(pexels_image(query,page=page))

    ##mix
    minv = min(len(pix_res),len(pex_res))
    fres = []
    for tmp in range(minv):
        fres.append(pex_res[tmp])
        fres.append(pix_res[tmp])
    fres += pix_res[minv:] + pex_res[minv:]
    print('Total Images: ',len(fres))
    return fres


def processPixabayVideo(results,addSource=False):
    allData = []
    for item in results["hits"]:
        name = item['tags']
        _lowVideoObj = item['videos']['tiny']
        high_res = None
        _obj = None
        for vid in item['videos']:
            if item['videos'][vid]['width']>=1920 or item['videos'][vid]['height']>=1920:
                high_res = item['videos'][vid]['url']
                _obj = item['videos'][vid]
                break
        if not high_res:
            high_res = item['videos']['large']['url']

        if high_res != '':
            #_lowVideoObj = high_res.replace('175','164')
            fileInfo = json.dumps({"duration": item["duration"]})
            _data = json.dumps({"thumbnail": f"https://i.vimeocdn.com/video/{item['picture_id']}_{_obj['width']}x{_obj['height']}.jpg","height": _obj["height"],"width": _obj["width"],"tags": vid["tags"]})
            if addSource:
                allData.append({'name': name,'low_url': _lowVideoObj,'high_url': high_res,"thumbnail": f"https://i.vimeocdn.com/video/{item['picture_id']}_{_lowVideoObj['width']}x{_lowVideoObj['height']}.jpg","fileInfo": fileInfo,"data": _data,"source": "pixabay"})
            else:
                allData.append({'name': name,'low_url': _lowVideoObj,'high_url': high_res,"thumbnail": f"https://i.vimeocdn.com/video/{item['picture_id']}_{_lowVideoObj['width']}x{_lowVideoObj['height']}.jpg","fileInfo": fileInfo,"data": _data})
    return allData

def processPexelsVideo(results,addSource=False):
    allData = []
    for n,vid in enumerate(results['videos']):
        try:
            _allVidHeight = []
            _allVideos = []
            for _vidO in vid['video_files']:
                if _vidO["height"]:
                    _allVidHeight.append(_vidO["height"])
                    _allVideos.append(_vidO)
            _sortedIndex = np.argsort(np.array(_allVidHeight))

            #_allVideos = sorted([[_vidO["height"],_vidO] for _vidO in vid['video_files'] if _vidO["height"]])
            if len(_allVideos)<=0:
                continue
            _lowVideoObj = _allVideos[_sortedIndex[0]]
            _vidObj = None
            # is Horizontal
            if _allVideos[0]["width"]>=_allVideos[0]['height']:
                for _vIndex in _sortedIndex:
                    if _allVidHeight[_vIndex]>=1080:
                        _vidObj =_allVideos[_vIndex]
                        break
            else:
                for _vIndex in _sortedIndex:
                    if _allVidHeight[_vIndex]>=1920:
                        _vidObj = _allVideos[_vIndex]
                        break
            if not _vidObj:
                _vidObj = _allVideos[_sortedIndex[-1]]

            name = ' '.join(vid['url'].split('video/')[-1].split('-')[:-1])
            thumbnail = vid['image'].split('?')[0]+f'?fit=crop&w={_lowVideoObj["width"]}&h={_lowVideoObj["height"]}&auto=compress&cs=tinysrgb'
            fileInfo = json.dumps({"duration": vid["duration"]})
            _data = json.dumps({"thumbnail": vid['image'].split('?')[0]+f'?fit=crop&w={_vidObj["width"]}&h={_vidObj["height"]}&auto=compress&cs=tinysrgb',"height": _vidObj["height"],"width": _vidObj["width"],"tags": ','.join(vid["tags"])})
            if addSource:
                allData.append({'name': name,'low_url': _lowVideoObj["link"],'high_url': _vidObj["link"],'thumbnail': thumbnail,"fileInfo": fileInfo,"data": _data,"source": "pexels"})
            else:
                allData.append({'name': name,'low_url': _lowVideoObj["link"],'high_url':  _vidObj["link"],'thumbnail': thumbnail,"fileInfo": fileInfo,"data": _data})
        except:
            pass
    return allData


  
def fetch_video(query,page,per_page = per_page,appType=1):
    def pixabay_video(query,page=1):
        inst, created = VideoSearch.objects.get_or_create(query_string=query,provider_name="pixabay",provider_page=page)
        if not created:
            if appType ==1:
                filter_query = VideoApiRes.objects.filter(query=inst)
            else:
                filter_query = APIVideoQuerySaver.objects.filter(query=inst)
            if filter_query:
                return filter_query

        try:
            fdata = []
            res = PIXABAY_VIDEO.search(q=query,
                    order='latest',
                    min_width=1920,
                    min_height=1080,
                    page=page,
                    per_page=per_page)

            parseData = processPixabayVideo(res)
            for _data in parseData:
                _data["query"] = inst
                if appType==1:
                    fdata.append(VideoApiRes(**_data))
                else:
                    fdata.append(APIVideoQuerySaver(**_data))
   
            if appType==1:
                fdata = VideoApiRes.objects.bulk_create(fdata)
            else:
                fdata = APIVideoQuerySaver.objects.bulk_create(fdata)
        except:
            fdata = []

        if appType ==1:
            _filterQuery = VideoApiRes.objects.filter(query=inst)
        else:
            _filterQuery = APIVideoQuerySaver.objects.filter(query=inst)

        return _filterQuery

    def pexels_video(query,page=1):
        inst, created = VideoSearch.objects.get_or_create(query_string=query,provider_name="pexels",provider_page=page)
        if not created:
            if appType ==1:
                filter_query = VideoApiRes.objects.filter(query=inst)
            else:
                filter_query = APIVideoQuerySaver.objects.filter(query=inst)

            if filter_query:
                return filter_query
        try:
            fdata = []
            res_data = py_pexels.videos_search(query=query,per_page=per_page,page=page,min_width=1920,size="medium",orientation="landscape")
            parseData = processPexelsVideo(res_data.body)
            for _data in parseData:
                _data["query"] = inst
                if appType==1:
                    fdata.append(VideoApiRes(**_data))
                else:
                    fdata.append(APIVideoQuerySaver(**_data))

            if appType==1:
                fdata = VideoApiRes.objects.bulk_create(fdata)
            else:
                fdata = APIVideoQuerySaver.objects.bulk_create(fdata)
        except:
            fdata = []

        if appType ==1:
            _filterQuery = VideoApiRes.objects.filter(query=inst)
        else:
            _filterQuery = APIVideoQuerySaver.objects.filter(query=inst)

        return _filterQuery

    pix_res = list(pixabay_video(query,page=page))
    pex_res = list(pexels_video(query,page=page))

    ##mix
    minv = min(len(pix_res),len(pex_res))

    fres = []
    for tmp in range(minv):
        fres.append(pex_res[tmp])
        fres.append(pix_res[tmp])
    fres += pix_res[minv:] + pex_res[minv:]
    print('Total Videos: ',len(fres))
    return fres

# page start from 1
def fetchVideo(query,page,per_page = per_page):
    TOTAL_PROVIDER = 2
    CRNT_PAGE_START_INDEX = per_page*(page-1)*TOTAL_PROVIDER
    def pixabay_video(query,page=1,QUERY_TTL=172800): # 2*24*60*60
        PROVIDER = "pixabay"
        _checker,ct = ApiQueryLogger.objects.get_or_create(query=query,page=page,providerName=PROVIDER,_type=1)
        if _checker.state==1:
            return 3

        _query = APIVideoQuerySaver.objects.filter(_queryString=query,_page=page,_apiProvider=PROVIDER)
        if _query:
            _first = _query.first()
            _updatedDiff = timezone.now() - _first.timestamp
            if _updatedDiff.total_seconds()<QUERY_TTL:
                return 1
            else:
                _query = APIVideoQuerySaver.objects.filter(_queryString=query,_apiProvider=PROVIDER)
                _query.delete()
                query = ApiQueryLogger.objects.filter(query=query,providerName=PROVIDER,_type=1)
                query.delete()
                page = 1
        try:
            _checker.state = 1
            _checker.save()
            fdata = []
            res = PIXABAY_VIDEO.search(q=query,
                    order='latest',
                    page=page,
                    per_page=per_page)

            parseData = processPixabayVideo(res)
            for _n,_data in enumerate(parseData):
                _data["_queryString"] = query
                _data["_page"] = page
                _data["_apiProvider"] = PROVIDER
                _data["_order"] = CRNT_PAGE_START_INDEX + (_n*TOTAL_PROVIDER)
                fdata.append(APIVideoQuerySaver(**_data))
            fdata = APIVideoQuerySaver.objects.bulk_create(fdata)
            _checker.state = 2
            _checker.save()
            return 2
        except:
            logger.error(f"fetchVideo:pixabay_video: {str(traceback.format_exc())}")
            _checker.state = 0
            _checker.save()
            return 0

    def pexels_video(query,page=1,QUERY_TTL=172800): # 2*24*60*60
        PROVIDER = "pexels"
        _checker,ct = ApiQueryLogger.objects.get_or_create(query=query,page=page,providerName=PROVIDER,_type=1)
        if _checker.state==1:
            return 3
        _query = APIVideoQuerySaver.objects.filter(_queryString=query,_page=page,_apiProvider=PROVIDER)
        if _query:
            _first = _query.first()
            _updatedDiff = timezone.now() - _first.timestamp
            if _updatedDiff.total_seconds()<QUERY_TTL:
                return 1
            else:
                _query = APIVideoQuerySaver.objects.filter(_queryString=query,_apiProvider=PROVIDER)
                _query.delete()
                query = ApiQueryLogger.objects.filter(query=query,providerName=PROVIDER,_type=1)
                query.delete()
                page = 1
        
        try:
            _checker.state = 1
            _checker.save()
            fdata = []
            res_data = py_pexels.videos_search(query=query,per_page=per_page,page=page)
            parseData = processPexelsVideo(res_data.body)
            for _n,_data in enumerate(parseData):
                _data["_queryString"] = query
                _data["_page"] = page
                _data["_apiProvider"] = PROVIDER
                _data["_order"] = CRNT_PAGE_START_INDEX + (_n*TOTAL_PROVIDER) +1
                fdata.append(APIVideoQuerySaver(**_data))
            fdata = APIVideoQuerySaver.objects.bulk_create(fdata)
            _checker.state = 2
            _checker.save()
            return 2
        except:
            logger.error(f"fetchVideo:pexels_video: {str(traceback.format_exc())}")
            _checker.state = 0
            _checker.save()
            return 0

    pool = ThreadPool(TOTAL_PROVIDER)
    results = []
    results.append(pool.apply_async(pixabay_video, args=(query,page)))
    results.append(pool.apply_async(pexels_video, args=(query,page)))
    pool.close()
    pool.join()
    results = [f"{r.get()}" for r in results]
    
    return " ".join(results)


#type (image,video)
#page (page from 1)
import requests
from django.utils import timezone

def getPixabayPopulaVideos(totalItem=100,addSource=True):
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&per_page={totalItem}&order=latest")#&min_width=1920&min_height=1080")
        return processPixabayVideo(r.json(),addSource=addSource)
    except:
        return []


def getPixabayPopulaImages(totalItem=100,addSource=True):
    # order "popular", "latest"
    try:
        r = requests.get(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&per_page={totalItem}&order=popular")
        return processPixabayImage(r.json(),addSource=addSource)
    except:
        return []

def getPexelsPopulaVideos(totalItem=100,addSource=True):
    try:
        res_data = py_pexels.videos_popular(per_page=totalItem)#,min_width=1920,size="medium",orientation="landscape")
        return processPexelsVideo(res_data.body,addSource=addSource)
    except:
        return []

def getPexelsPopulaImages(totalItem=100,addSource=True):
    try:
        res_data = py_pexels.popular(per_page=totalItem)
        return processPexelsImage(res_data.body,addSource=addSource)
    except:
        return []

def fetch_popular_video(totalItem=100,refrestTime=36000): #60*60*20
    _allInst = APIVideoPopularSaver.objects.all()
    #check if updated is less
    if _allInst.count():
        _first = _allInst.first()
        _updatedDiff = timezone.now() - _first.timestamp
        if _updatedDiff.total_seconds()<refrestTime:
            return _allInst
        
    allPixabayData = getPixabayPopulaVideos(totalItem=totalItem,addSource=True)
    allPexelsData = getPexelsPopulaVideos(totalItem=totalItem,addSource=True)

    result = list(roundrobin(allPexelsData,allPixabayData))
    
    if len(result)>10:
        if _allInst.count():
            _allInst.delete()
        allInst = []
        for _item in result:
            allInst.append(APIVideoPopularSaver(**_item))
        fdata = APIVideoPopularSaver.objects.bulk_create(allInst)
        _allInst = APIVideoPopularSaver.objects.all()

    return _allInst


def fetch_popular_images(totalItem=100,refrestTime=36000,forceUpdate=False): #60*60*20
    _allInst = APIImagePopularSaver.objects.all()
    #check if updated is less
    if _allInst.count() and forceUpdate==False:
        _first = _allInst.first()
        _updatedDiff = timezone.now() - _first.timestamp
        if _updatedDiff.total_seconds()<refrestTime:
            return _allInst
    
    pool = ThreadPool(3)
    results = []
    results.append(pool.apply_async(getPixabayPopulaImages, args=(totalItem,True)))
    results.append(pool.apply_async(getPexelsPopulaImages, args=(totalItem,True)))
    results.append(pool.apply_async(unsplashPopularImages, args=(totalItem,True)))
    pool.close()
    pool.join()
    results = [r.get() for r in results]
    allPixabayData = results[0]
    allPexelsData = results[1]
    allUnsplashData = results[2]

    result = list(roundrobin(allPexelsData,allPixabayData,allUnsplashData))
    
    if len(result)>10:
        if _allInst.count():
            _allInst.delete()
        allInst = []
        for _item in result:
            allInst.append(APIImagePopularSaver(**_item))
        fdata = APIImagePopularSaver.objects.bulk_create(allInst)
        _allInst = APIImagePopularSaver.objects.all()

    return _allInst




from rest_framework.pagination import LimitOffsetPagination
class LimitOffset(LimitOffsetPagination):
    default_limit =5
    max_limit = 50


class FilterBackground(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    #serializer_class = UserSerializer

    def get(self, request, format=None):
        params = request.GET

        try:
            limitG = int(params.get('limit','5'))
            offsetG = int(params.get('offset','5'))
        except:
            limitG = 5
            offsetG = 5
        page = 1 + (limitG+offsetG)//per_page

        query = params.get('query','')
        if query:
            if 'type' in params:
                if params['type'] == 'video':
                    query = fetch_video(query,page)
                    serializer_class = VideoApiResSerializer 
                else:
                    query = fetch_image(query,page)
                    serializer_class = ImageApiResSerializer 
            else:
                query = fetch_image(query,page)
                serializer_class = ImageApiResSerializer
            results = self.paginate_queryset(query, request, view=self)
            serializer = serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            if 'type' in params:
                if params['type'] == 'video':
                    query = VideoApiRes.objects.all().order_by('name')
                    serializer_class = VideoApiResSerializer 
                else:
                    query = ImageApiRes.objects.all().order_by('name')
                    serializer_class = ImageApiResSerializer 
            else:
                query = ImageApiRes.objects.all().order_by('name')#.order_by('?')
                serializer_class = ImageApiResSerializer
            results = self.paginate_queryset(query, request, view=self)
            serializer = serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)

from backgroundclip import task as backgroundClipTask

class APIVideoView(APIView,LimitOffset):
    permission_classes = (IsAuthenticated,)
    #serializer_class = UserSerializer

    def get(self, request, format=None):
        params = request.GET

        try:
            limitG = int(params.get('limit','5'))
            offsetG = int(params.get('offset',0))
        except:
            limitG = 5
            offsetG = 0
        page = 1 + (limitG+offsetG)//per_page

        _query = params.get('query','')
        query = ""

        if _query:
            if 'type' in params:
                if params['type'] == 'video':
                    _res = fetchVideo(_query,page)
                    backgroundClipTask.saveNextPageData.delay({"type": "video","page": page+1,"query": _query})
                    query = APIVideoQuerySaver.objects.filter(_queryString=_query)
                    serializer_class = APIVideoSerializer
                else:
                    _res = newAPIFetchImage(_query,page)
                    backgroundClipTask.saveNextPageData.delay({"type": "image","page": page+1,"query": _query})
                    query = APIImageQuerySaver.objects.filter(_queryString=_query)
                    serializer_class = APIImageSerializer 
            else:
                _res = newAPIFetchImage(_query,page)
                backgroundClipTask.saveNextPageData.delay({"type": "image","page": page+1,"query": _query})
                query = APIImageQuerySaver.objects.filter(_queryString=_query)
                serializer_class = APIImageSerializer
            results = self.paginate_queryset(query, request, view=self)
            serializer = serializer_class(results, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
        else:
            if 'type' in params:
                if params['type'] == 'video':
                    query = fetch_popular_video()
                    results = self.paginate_queryset(query, request, view=self)
                    serializer = APIVideoPopularSerializer(results, many=True,context={'request': request})
                    return self.get_paginated_response(serializer.data)
                else:
                    query = fetch_popular_images()
                    serializer_class = APIImagePopularSerializer 
            else:
                query = fetch_popular_images()
                serializer_class = APIImagePopularSerializer
            results = self.paginate_queryset(query, request, view=self)
            serializer = serializer_class(results, many=True,context={'request': request})
            if offsetG != 0:
                return self.get_paginated_response(serializer.data)
            _crntData = self.get_paginated_response(serializer.data).data.copy()
            _variableData =  [{"id": 0,"ctg": 1,"name": "Variable","media_file":"https://api.autogenerate.ai/media/ImageMergeTagDefault.webp"}]
            _crntData["results"] = _variableData + _crntData["results"]
            return Response(_crntData,status=status.HTTP_200_OK)



#type image or video
class SaveAPIData(APIView):
    permission_classes = (IsAuthenticated,)
    #serializer_class = UserSerializer

    def post(self, request, format=None):
        params = request.data

        if 'id' in params and 'type' in params:
            type_ = params['type']
            try:
                id_ = int(params['id'])
            except:
                return Response({"detail": "id is not valid"},status=404)
            try:
                if type_ == 'image':
                    obj = ImageApiRes.objects.get(id=id_)
                elif type_ == 'video':
                    obj = VideoApiRes.objects.get(id=id_)
                else:
                    return Response({"detail": "id is not valid"},status=404)
                obj.is_save = True
                obj.save()
                return Response({"success": "ok"})
            except:
                return Response({"detail": "id is not valid"},status=404)
        else:
            return Response({"detail": "id and type is Required"},status=404)



class LimitOffsetM(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50

    def paginate_queryset(self, count, request, view=None):
        self.limit = self.get_limit(request)#10
        if self.limit is None:
            return None

        self.count = count
        self.offset = self.get_offset(request)
        self.request = request
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []
        return []

class FilterAllView(APIView,LimitOffsetM):
    permission_classes = (IsAuthenticated,)
    #serializer_class = UserSerializer

    def get(self, request, format=None):
        params = request.GET

        try:
            limitG = int(params.get('limit','12'))#10
            offsetG = int(params.get('offset','0'))
        except:
            limitG = 12
            offsetG = 0


        page = 1 + (limitG+offsetG)//per_page

        query = params.get('query','')
        if query:
            type_ = 'image'
            if 'type' in params:
                if params['type'] == 'video':
                    type_ = 'video'

            fileUploadQuery = FileUpload.objects.filter(user=request.user,media_type__icontains=type_,name__icontains=query,category='upload').order_by('-timestamp')
            fileQCount =  fileUploadQuery.count()

            limitPQ = limitG//2
            stpoint = 0
            ltpoint = 0
            #new concept
            fNo = fileQCount//limitPQ
            fRm = fileQCount%limitPQ
            fileIndex = [limitPQ] * fNo + [fRm]
            apiIndex = [limitG-limitPQ]*fNo + [limitG-fRm]
            crntIndex = (limitG+offsetG)//limitG

            stpoint = 0
            ltpoint = 0
            if crntIndex<=len(fileIndex):
                if crntIndex==1:
                    fileUploadQueryC = list(fileUploadQuery[0:sum(fileIndex[0:crntIndex])])
                    stpoint = 0
                    ltpoint = sum(apiIndex[0:crntIndex])
                else:
                    fileUploadQueryC = list(fileUploadQuery[sum(fileIndex[0:crntIndex-1]):sum(fileIndex[0:crntIndex])])
                    stpoint = sum(apiIndex[0:crntIndex-1])
                    ltpoint = sum(apiIndex[0:crntIndex])
            else:
                fileUploadQueryC = []
                stpoint = sum(apiIndex[0:crntIndex]) + (limitG * (crntIndex-len(fileIndex)-1))
                ltpoint = sum(apiIndex[0:crntIndex]) + (limitG * (crntIndex-len(fileIndex)))
            # halfQC = (limitG+offsetG)//2
            # limitPQ = limitG//2
            # stpoint = 0
            # ltpoint = 0
            # if halfQC <= fileQCount:
            #     #page = 1 + (limitG+offsetG - halfQC)//per_page
            #     fileUploadQueryC = list(fileUploadQuery[halfQC-limitPQ:halfQC])
            #     stpoint = halfQC-limitPQ
            #     ltpoint = offsetG+limitG-len(fileUploadQueryC)#halfQC
            # else:
            #     halfQCT = fileQCount-(offsetG//2)
            #     if halfQCT<=0:
            #         fileUploadQueryC = []
            #         stpoint =offsetG - (fileQCount%limitPQ)
            #         ltpoint = stpoint+limitG
            #     else:
            #         fileUploadQueryC = list(fileUploadQuery[halfQC-limitPQ:fileQCount])
            #         stpoint =halfQC-limitPQ
            #         ltpoint = offsetG+limitG-len(fileUploadQueryC)

            fileFRes = FileUploadSerializer(fileUploadQueryC, many=True,context={'request': request}).data
            page = ltpoint//per_page
            if type_=='video':
                apiQuery = fetch_video(query,page)
                serializerR = VideoApiResSerializer(list(apiQuery[stpoint:ltpoint]), many=True,context={'request': request}).data
            else:
                apiQuery = fetch_image(query,page)
                serializerR = ImageApiResSerializer(list(apiQuery[stpoint:ltpoint]), many=True,context={'request': request}).data

            results = fileFRes + serializerR
            count = fileQCount + len(apiQuery)
            t = self.paginate_queryset(count,request)
            return self.get_paginated_response(results)

        else:
            type_ = 'image'
            if 'type' in params:
                if params['type'] == 'video':
                    type_ = 'video'

            fileUploadQuery = FileUpload.objects.filter(user=request.user,media_type__icontains=type_,category='upload').order_by('-timestamp')
            fileQCount =  fileUploadQuery.count()
            limitPQ = limitG//2

            #new concept
            fNo = fileQCount//limitPQ
            fRm = fileQCount%limitPQ
            fileIndex = [limitPQ] * fNo + [fRm]
            apiIndex = [limitG-limitPQ]*fNo + [limitG-fRm]
            crntIndex = (limitG+offsetG)//limitG

            stpoint = 0
            ltpoint = 0
            if crntIndex<=len(fileIndex):
                if crntIndex==1:
                    fileUploadQueryC = list(fileUploadQuery[0:sum(fileIndex[0:crntIndex])])
                    stpoint = 0
                    ltpoint = sum(apiIndex[0:crntIndex])
                else:
                    fileUploadQueryC = list(fileUploadQuery[sum(fileIndex[0:crntIndex-1]):sum(fileIndex[0:crntIndex])])
                    stpoint = sum(apiIndex[0:crntIndex-1])
                    ltpoint = sum(apiIndex[0:crntIndex])
            else:
                fileUploadQueryC = []
                stpoint = sum(apiIndex[0:crntIndex]) + (limitG * (crntIndex-len(fileIndex)-1))
                ltpoint = sum(apiIndex[0:crntIndex]) + (limitG * (crntIndex-len(fileIndex)))


            # halfQC = (limitG+offsetG)//2
            # if halfQC <= fileQCount:
            #     fileUploadQueryC = list(fileUploadQuery[halfQC-limitPQ:halfQC])
            #     stpoint = halfQC-limitPQ
            #     ltpoint = offsetG+limitG-len(fileUploadQueryC)#halfQC
            # else:
            #     halfQCT = fileQCount-(offsetG//2)
            #     if halfQCT<=0:
            #         fileUploadQueryC = []
            #         stpoint =offsetG - (fileQCount%limitPQ)
            #         ltpoint = stpoint+limitG
            #     else:
            #         fileUploadQueryC = list(fileUploadQuery[halfQC-limitPQ:fileQCount])
            #         stpoint =halfQC-limitPQ
            #         ltpoint = offsetG+limitG-len(fileUploadQueryC)
            fileFRes = FileUploadSerializer(fileUploadQueryC, many=True,context={'request': request}).data
            if type_=='video':
                apiQuery = VideoApiRes.objects.all().order_by('name')
                serializerR = VideoApiResSerializer(list(apiQuery[stpoint:ltpoint]), many=True,context={'request': request}).data
            else:
                apiQuery = ImageApiRes.objects .all().order_by('name')
                serializerR = ImageApiResSerializer(list(apiQuery[stpoint:ltpoint]), many=True,context={'request': request}).data

            results = fileFRes + serializerR
            count = fileQCount + apiQuery.count()
            t = self.paginate_queryset(count,request)
            return self.get_paginated_response(results)




from shutil import copy
from multiprocessing import Process
from threading import Thread
def updateLowQualityVideoToHigh(id,url):
    _inst = APISaveVideo.objects.get(id=id)
    download_file(url,_inst.getVideoPath())
    return True
    
def extractVideoFrames(id):
    _inst = APISaveVideo.objects.get(id=id)
    _inst.extractFrames()
    return True

class ProcessApiVideo(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = APISaveVideoSerializer

    def get_object(self, pk,category,user):
        try:
            _inst = None
            if category==0:
                try:
                    _inst = APIVideoQuerySaver.objects.get(pk=pk)
                except:
                    pass
            elif category==1:
                try:
                    _inst = APIVideoPopularSaver.objects.get(pk=pk)
                except:
                   pass
            elif category==2:
                try:
                    _inst = FileUpload.objects.get(pk=pk)
                    if not _inst.isPublic and _inst.user.id != user.id:
                        return (False,_inst)
                except:
                    pass
            if _inst:
                return (True,_inst)
            return (False,_inst)
        except:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        _type = convertInt(request.GET.get("ctg",0))
        is_exist,inst = self.get_object(pk,_type,user)
        if is_exist:
            _inst,ct = APISaveVideo.objects.get_or_create(apiVideoInstId=inst.id,apiVideoInstType=_type)
            if ct:
                ## download original Video
                _inst.user = user
                _inst.name = inst.name
                if _type==0 or _type == 1:
                    _originalVideoUrl = inst.high_url #inst.low_url
                    _thumbnailUrl,_tags = inst.getThumbnailUrlAndTags()
                    try:
                        download_file(_originalVideoUrl,_inst.getVideoPath())
                        if _thumbnailUrl:
                            download_file(_thumbnailUrl,_inst.getThumbnailPath())
                        ## process it
                        _inst.srcUrl = _originalVideoUrl
                        _inst.originalVideo.name = _inst.getVideoName()
                        _inst.thumbnail.name = _inst.getThumbnailName()
                        _inst.save()
                        _inst.convertPreview()
                        # _th = Process(target=updateLowQualityVideoToHigh,args=(_inst.id,inst.high_url))
                        # _th.start()
                    except:
                        content = {'detail': 'Api Video Url not found.',"isError": True}
                        return Response(content,status=status.HTTP_200_OK)
                else:
                    if inst.media_type == 'video/webm':
                        _inst.isTransparent = True
                        _inst.save()
                    # user upload
                    _originalFilePath = inst.media_file.path
                    _originalThumbnailPath = inst.media_thumbnail.path
                    copy(_originalFilePath,_inst.getVideoPath())
                    copy(_originalThumbnailPath,_inst.getThumbnailPath())
                    _inst.originalVideo.name = _inst.getVideoName()
                    _inst.thumbnail.name = _inst.getThumbnailName()
                    _inst.save()
                    _inst.convertPreview(isFileUpload=True)
                    _th = Thread(target=extractVideoFrames,args=(_inst.id,))
                    _th.start()
                    
            serializer = self.serializer_class(_inst,context={'request': request})
            content = {'result': serializer.data,"isError": False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist',"isError": True}
            return Response(content,status=status.HTTP_200_OK)
    


class ProcessApiImage(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = APISaveImageSerializer

    def get_object(self, pk,category,user):
        try:
            _inst = None
            if category==0:
                try:
                    _inst = APIImageQuerySaver.objects.get(pk=pk)
                except:
                    pass
            elif category==1:
                try:
                    _inst = APIImagePopularSaver.objects.get(pk=pk)
                except:
                   pass
            elif category==2:
                try:
                    _inst = FileUpload.objects.get(pk=pk)
                    if not _inst.isPublic and _inst.user.id != user.id:
                        return (False,_inst)
                except:
                    pass
            elif category==3:
                try:
                    _inst = VideoGradientColor.objects.get(pk=pk)
                except:
                    pass
            if _inst:
                return (True,_inst)
            return (False,_inst)
        except:
            return (False,'')

    def get(self, request,pk, format=None):
        user = request.user
        _type = convertInt(request.GET.get("ctg",0))
        if _type == 1:
            if pk == 0:
                _crntData = {"id": 0,"name": "Variable","ctg": 1,"media_file":"https://api.autogenerate.ai/media/ImageMergeTagDefault.webp","image":"https://api.autogenerate.ai/media/ImageMergeTagDefault.webp","fileInfo": {"height": 1080,"width": 1920}}
                content = {'result': _crntData,"isError": False}
                return Response(content,status=status.HTTP_200_OK)
        is_exist,inst = self.get_object(pk,_type,user)
        if is_exist:
            _inst,ct = APISaveImage.objects.get_or_create(apiVideoInstId=inst.id,apiVideoInstType=_type)
            if ct:
                ## download original Video
                _inst.user = user
                _inst.name = inst.name
                if _type==0 or _type == 1:
                    download_file(inst.high_url,_inst.getImagePath())
                    _inst.image.name = _inst.getImageName()
                    _inst.save()
                else:
                    _originalFilePath = inst.media_file.path
                    copy(_originalFilePath,_inst.getImagePath())
                    _inst.image.name = _inst.getImageName()
                    _inst.save()
                try:
                    _inst.convertImage()
                except:
                    _inst.delete()
                    content = {'detail': 'Url not Valid.',"isError": True}
                    return Response(content,status=status.HTTP_200_OK)

            serializer = self.serializer_class(_inst,context={'request': request})
            content = {'result': serializer.data,"isError": False}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist',"isError": True}
            return Response(content,status=status.HTTP_200_OK)
    


class ProcessApiVideoDetails(APIView):
    permission_classes = (AllowAny,)
    serializer_class = APISaveVideoServerSideSerializer

    def isValidUser(self,request):
        try:
            # validate token
            _token = request.GET.get('token',None)
            if _token == settings.SERVER_TOKEN:
                return (True,None)
            return (False,None)
        except:
            return (False,'')

    def post(self, request,pk, format=None):
        is_exist,inst = self.isValidUser(request)
        _videoId = request.data.get("videoId",None)
        if is_exist:
            finalData = {}
            if _videoId:
                try:
                    for _vid in _videoId:
                        try:
                            _inst = APISaveVideo.objects.get(id=_vid)
                            finalData[_vid] = self.serializer_class(_inst,context={'request': request}).data
                        except:
                            pass
                except:
                    pass
            content = {'result': finalData}
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {'detail': 'Object Doestnot Exist'}
            return Response(content,status=status.HTTP_404_NOT_FOUND)