from django.urls import path

from appAssets.views import (
    AvatarsImagesView,AvatarsImagesDetailView,
    AvatarsSoundView,AvatarsSoundDetailView,
    AvatarSoundCombinationView,
    VoiceLanguageView,
    GetAvatarVoicesView
)


urlpatterns = [
    path('image/', AvatarsImagesView.as_view()),
    path('image/<int:pk>/', AvatarsImagesDetailView.as_view()),
    path('sound/', AvatarsSoundView.as_view()),
    path('sound/<int:pk>/', AvatarsSoundDetailView.as_view()),
    path('avatar_sound/', AvatarSoundCombinationView.as_view()),
    path('voices/', VoiceLanguageView.as_view()),
    path('avatar_voices/', GetAvatarVoicesView.as_view()),

]
