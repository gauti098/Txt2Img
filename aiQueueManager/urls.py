from django.urls import path

from aiQueueManager.views import (
    GenerateVideoView,MergeTagView,
    MergeTagDetailView,
    VideoPublicTemplateView,
    VideoTemplateCopyView,SingleSceneView,
    SingleSceneAddView,VideoTemplateView,
    AllSingleSceneView,VideoTemplateDetailsView,BackgroundMusicView,
    GeneratingVideoDetailsView,GeneratingVideoView,SnapshotUrlView,AllTemplateDataView,
    VideoDetailsView,VideoThumbnailView,VideoThemeTemplateView,
    VideoTemplateCreateView,VideoTemplateSaveView,
    VideoDetailsGenerateView,VideoDetailsGeneratingView,
    VideoGradientView
)

urlpatterns = [
    
    #path('colors/', ColorsView.as_view()),
    #path('colors/<int:pk>/', ColorsView.as_view()), #completed
    #path('colors/<int:pk>/', ColorsDetailView.as_view()),


    path('mergetag/', MergeTagView.as_view()),
    path('mergetag/<int:pk>/', MergeTagDetailView.as_view()),
    path('drafts/', VideoTemplateView.as_view()), #completed


    path('template/<int:pk>/', VideoTemplateDetailsView.as_view()), #completed
    path('template/<int:pk>/all/', AllTemplateDataView.as_view()), #completed
    path('template/public/', VideoPublicTemplateView.as_view()), # remove it
    path('template/<int:pk>/copy/', VideoTemplateCopyView.as_view()), #completed
    path('template/scene/<int:pk>/',AllSingleSceneView.as_view()), #completed


    path('template/create/', VideoTemplateCreateView.as_view()), #completed
    path('scene/<int:pk>/', SingleSceneView.as_view()),  #completed
    path('scene/<int:pk>/add/', SingleSceneAddView.as_view()), #completed
    path('template/<int:pk>/save/', VideoTemplateSaveView.as_view()), #completed (after work disable single update)


    path('music/', BackgroundMusicView.as_view()), #completed
    path('gradient/', VideoGradientView.as_view()), #completed
    path('snapshot/<int:pk>/', SnapshotUrlView.as_view()),

    path('template/<int:pk>/generate/', GenerateVideoView.as_view()),
    path('video/<int:pk>/details/', VideoDetailsView.as_view()),
    path('generated/video/<int:pk>/',GeneratingVideoDetailsView.as_view()), #completed
    path('generated/video/', GeneratingVideoView.as_view()),


    path('video/thumbnail/<int:pk>/', VideoThumbnailView.as_view()),
    path('videotemplate/', VideoThemeTemplateView.as_view()), #completd

    ## generate Video from details
    path('video/details/<int:pk>/', VideoDetailsGeneratingView.as_view()),
    path('video/details/<int:pk>/generate/', VideoDetailsGenerateView.as_view()),


]