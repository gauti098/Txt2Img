from django.db.models import query
from backgroundclip.models import (
    ImageApiRes,
    ImageSearch
)
from videoAutomation.settings import BASE_URL

from datetime import datetime, timedelta
from django.utils import timezone
today = timezone.now()
yesterday = today - timedelta(days=1)


allOldData = ImageSearch.objects.filter(timestamp__lte=yesterday,provider_name = 'pixabay')
for cid in allOldData:
    allD = ImageApiRes.objects.filter(query=cid,is_save=False)
    for tid in allD:
        tid.delete()
    allD = ImageApiRes.objects.filter(query=cid,is_save=True)
    for tid in allD:
        url = BASE_URL+ tid.image.url
        tid.low_url = url
        tid.high_url = url
        tid.save()

    cid.delete()


# allOldData = VideoSearch.objects.filter(timestamp__lte=yesterday,provider_name = 'pixabay')
# for cid in allOldData:
#     allD = ImageApiRes.objects.filter(query=cid,is_save=False)
#     for tid in allD:
#         tid.delete()
#     allD = ImageApiRes.objects.filter(query=cid,is_save=True)
#     for tid in allD:
#         url = BASE_URL+ tid.image.url
#         tid.low_url = url
#         tid.high_url = url
#         tid.save()

#     cid.delete()