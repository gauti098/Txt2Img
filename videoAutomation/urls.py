
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls import url

from campaignAnalytics.views import CampaignThumbnailViews
from urlShortner.views import campaignUrlRedirect

from newImageEditor.views import imageCreatorThubmnailFileView


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/accounts/', include('accounts.urls')),
    path('api/accounts/', include('authemail.urls')),
    path('api/bgclip/', include('backgroundclip.urls')),
    path('api/userlibrary/',include('userlibrary.urls')),
    path('api/salespage/',include('salesPage.urls')),
    path('api/aivideo/',include('aiQueueManager.urls')),
    path('api/avatars/',include('appAssets.urls')),
    path('api/campaign/',include('campaign.urls')),

    path('api/canalytics/',include('campaignAnalytics.urls')),
    path('api/videocredit/',include('subscriptions.urls')),
    path('api/subscription/',include('videoCredit.urls')),
    path('campaign/thumbnail/',CampaignThumbnailViews.as_view()),
    path('api/videothumbnail/',include('videoThumbnail.urls')),
    path('api/audio/',include('aiAudio.urls')),

    path('api/newvideo/',include('newVideoCreator.urls')),
    path('api/newimage/',include('newImageEditor.urls')),

    ## new video creator
    path('api/assets/',include('externalAssets.urls')),
    
    #user colors
    path('api/colors/',include('colors.urls')),
    
    path('api/payment/',include('paymentHandler.urls')),

    # special urls
    path("c/<str:slugs>", campaignUrlRedirect, name="campaignredirect"),
    path("i/<str:slugs>", imageCreatorThubmnailFileView, name="image_creator_thumbnail_view")

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 