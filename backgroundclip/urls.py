from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from backgroundclip.views import (
    FilterAllView,FilterBackground,
    SaveAPIData,ProcessApiVideo,
    APIVideoView,ProcessApiVideoDetails,
    ProcessApiImage
)


urlpatterns = [
    path('filter/all/', FilterAllView.as_view(), name='filterall'),
    path('filter/', FilterBackground.as_view(), name='filter-background-clip'),
    path('search/', APIVideoView.as_view(), name='new-background-clip-filter'),
    path('save/', SaveAPIData.as_view(), name='save-background-clip'),
    path('process/video/<int:pk>/', ProcessApiVideo.as_view(), name='process-api-video'),
    path('process/image/<int:pk>/', ProcessApiImage.as_view(), name='process-api-image'),
    #path('process/video/details/', ProcessApiVideoDetails.as_view(), name='process-api-video-details'),
]


urlpatterns = format_suffix_patterns(urlpatterns)
