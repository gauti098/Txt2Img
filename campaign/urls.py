from django.urls import path,include

from campaign.views import (
    CampaignListView,CampaignDetailView,
    SoloCampignView,SoloCampignDetailsView,
    GroupCampignView,GroupCampignValidateView,
    GroupSingleCampignView,GroupCampignGenerateView,
    CampaignTestEmailView,CampaignListMinView,
    SalesPageLinkedCampaignView,VideoLinkedCampaignView,
    EmailClientView
)

urlpatterns = [
    path('linked/<int:pk>/salespage/', SalesPageLinkedCampaignView.as_view()),
    path('linked/<int:pk>/video/', VideoLinkedCampaignView.as_view()),

    path('<uuid:pk>/', CampaignDetailView.as_view()),
    path('<uuid:pk>/solo/', SoloCampignView.as_view()),

    ## manage group create or fetch or validate
    path('<uuid:pk>/group/', GroupCampignView.as_view()), #fetch group listing
    path('<uuid:pk>/group/validate/', GroupCampignValidateView.as_view()),
    path('<uuid:pk>/group/generate/', GroupCampignGenerateView.as_view()),


    path('details/<str:pk>/', SoloCampignDetailsView.as_view()),
    path('group/<uuid:pk>/', GroupSingleCampignView.as_view()),
    path('<uuid:pk>/test_email/', CampaignTestEmailView.as_view()),
    path('min/', CampaignListMinView.as_view()),
    path('emailclient/', EmailClientView.as_view()),
    path('', CampaignListView.as_view()),
]
