from django.urls import path

from aiAudio.views import (
    AiAudioGenerateView,AiAudioGenerateWithCombinationView,
    BatchAudioGenerateView
)


urlpatterns = [
    path('generate/', AiAudioGenerateView.as_view()),
    path('combine_generate/', AiAudioGenerateWithCombinationView.as_view()),
    path('batch/', BatchAudioGenerateView.as_view()),
]
