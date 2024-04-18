import json
from celery import shared_task
from backgroundclip.views import fetchVideo,newAPIFetchImage

@shared_task(bind=True)
def saveNextPageData(self,data):
    if data["type"] == "image":
        return newAPIFetchImage(data["query"],data["page"])
    elif data["type"] == "video":
        return fetchVideo(data["query"],data["page"])
