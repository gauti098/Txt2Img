from django.urls import path,include

from campaignAnalytics.views import (
    CampaignAnalyticsMainView,CampaignAnalyticsSignalView,
    EventCollectingView,CampaignAnalyticsSignalDetailsView,
    CampaignAnalyticsProspectView,CampaignAnalyticsProspectDetailsView,
    CampaignSoloBriefView,CampaignGroupBriefView,CampaignMailOGraphView,
    CampaignMailOEmailGraphView,CampaignVideoPGraphView,
    CampaignVideoPEmailGraphView,CampaignEngOGraphView,
    CampaignCTACAnalyticsView,CampaignCollateralAnalyticsView,
    CampaignAllBriefView,CampaignLinkOGraphView,
    CampaignLinkOEmailGraphView,DashboardProspectView,
    CampaignAnalyticsSignalManageView,CampaignGroupDetailsView
    
)


urlpatterns = [


    path('main/', CampaignAnalyticsMainView.as_view()),
    path('signal/', CampaignAnalyticsSignalView.as_view()),
    path('signal/manage/all/', CampaignAnalyticsSignalManageView.as_view()),
    path('signal/manage/<int:pk>/', CampaignAnalyticsSignalDetailsView.as_view()),

    path('prospects/', CampaignAnalyticsProspectView.as_view()),
    path('dashboard/prospects/', DashboardProspectView.as_view()),
    path('prospects/manage/', CampaignAnalyticsProspectDetailsView.as_view()),

    path('details/solo/', CampaignSoloBriefView.as_view()),
    path('details/group/', CampaignGroupBriefView.as_view()),
    path('details/groupdetails/', CampaignGroupDetailsView.as_view()),
    path('details/ongoing/', CampaignAllBriefView.as_view()),


    path('graph/mailo/', CampaignMailOGraphView.as_view()),
    path('emails/mailo/', CampaignMailOEmailGraphView.as_view()),

    path('graph/linko/', CampaignLinkOGraphView.as_view()),
    path('emails/linko/', CampaignLinkOEmailGraphView.as_view()),

    path('graph/videop/', CampaignVideoPGraphView.as_view()),
    path('emails/videop/', CampaignVideoPEmailGraphView.as_view()),


    path('graph/engm/', CampaignEngOGraphView.as_view()),

    path('ctad/', CampaignCTACAnalyticsView.as_view()),
    path('collaterald/', CampaignCollateralAnalyticsView.as_view()),
   
    path('<slug:data>/', EventCollectingView.as_view()),
]
