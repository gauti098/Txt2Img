from django.urls import path,include

from newVideoCreator.views import (
    TempVideoCreatorView,TempVideoCreatorDetailView,
    VideoAnimationView,VideoFilterView,
    TotalUsedUploadFileView, VideoTemplateView,
    GeneratedVideoView,DraftVideoView,CopyVideoView,
    VideoSceneAnimationView,VideoCreatorDetailsView,
    GenerateVideoView,UpdateVideoDraftThumbnailView,
    TextAnimationView,VideoSceneView,InsideVideoTemplateView,
    DownloadVideoGenerateView,FontsView,RenderCompleteVideoView,
    SoloVideoGenerateView,CSVValidaterView,SoloMailVideoGenerateView,
    GenerateCSVValidaterView,EmailGenerateHistoryView,EmailCSVHistoryDetailView,
    BatchGeneratedHistoryFileView,ThumbnailUpdateCallbackView,
    RealTimeNonAvatarMTagView
)

urlpatterns = [
    path('video/create/', TempVideoCreatorView.as_view()),
    path('video/template/', VideoTemplateView.as_view()),
    path('video_template/', InsideVideoTemplateView.as_view()),
    path('video/draft/', DraftVideoView.as_view()),
    path('video/generated/', GeneratedVideoView.as_view()),
    path('video/copy/<int:pk>/', CopyVideoView.as_view()),
    
    path('video/<int:pk>/', TempVideoCreatorDetailView.as_view()),
    path('video/scene/<int:pk>/', VideoSceneView.as_view()),
    path('video/details/<int:pk>/', VideoCreatorDetailsView.as_view()),

    path('video/generate/<int:pk>/', GenerateVideoView.as_view()),
    path('video/generate/download/<int:pk>/', DownloadVideoGenerateView.as_view()),
    path('video/generate/solo/<int:pk>/', SoloVideoGenerateView.as_view()),
    path('video/generate/solomail/<int:pk>/', SoloMailVideoGenerateView.as_view()),
    #validate csv
    path('video/batch/validate/<int:pk>/', CSVValidaterView.as_view()),
    path('video/batch/generate/<uuid:pk>/', GenerateCSVValidaterView.as_view()),
    path('video/generate/batch/<int:pk>/', EmailGenerateHistoryView.as_view()),
    path('video/details/batch/<uuid:pk>/', EmailCSVHistoryDetailView.as_view()),
    path('video/details/batch/<uuid:pk>/generated/', BatchGeneratedHistoryFileView.as_view()),

    #path('video/render/<int:pk>/', RenderVideoView.as_view()),
    path('video/render/<int:pk>/', RenderCompleteVideoView.as_view()),
    path('video/callback/thumbnail/<int:pk>/', ThumbnailUpdateCallbackView.as_view()),

    path('video/mtagData/<uuid:pk>/', RealTimeNonAvatarMTagView.as_view()),

    path('draftthumbnail/update/<int:pk>/', UpdateVideoDraftThumbnailView.as_view()),

    path('fileused/<int:pk>/', TotalUsedUploadFileView.as_view()),

    ## animation static api
    path('animation/', VideoAnimationView.as_view()),
    path('text/animation/', TextAnimationView.as_view()),
    path('animation/scene/', VideoSceneAnimationView.as_view()),
    path('filter/', VideoFilterView.as_view()),
    path('fonts/', FontsView.as_view()),


]
