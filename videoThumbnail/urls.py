from django.urls import path,include
from videoThumbnail.views import (
    MainThumbnailDetailView,MainThumbnailView,
    ThumbnailViewColorsView,ErrorCheck
)

urlpatterns = [
    path('thumbnail/', MainThumbnailView.as_view()),
    path('thumbnail/<int:pk>/', MainThumbnailDetailView.as_view()),
    path('color/<int:pk>/', ThumbnailViewColorsView.as_view()),
    path('error/', ErrorCheck.as_view()),
]
