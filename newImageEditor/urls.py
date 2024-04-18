from django.urls import path


from newImageEditor.views import (
    ImageCreatorView,
    ImageCreatorCreateView,ImageTemplateView,
    CopyImageCreatorView,ImageCreatorUpdateView,
    CopyVideoCreatorView,GenerateImageView,
    ImageCreatorDetailsView,GenerateImageThumbnailView,
    SaveTempleteView,GenerateImageLinkView
)


urlpatterns = [
    path('image/', ImageCreatorView.as_view()),
    path('image/create/', ImageCreatorCreateView.as_view()),
    path('image/template/', ImageTemplateView.as_view()),
    path('image/<int:pk>/', ImageCreatorUpdateView.as_view()),
    path('image/details/<int:pk>/', ImageCreatorDetailsView.as_view()),
    path('image/copy/<int:pk>/', CopyImageCreatorView.as_view()),
    path('video/copy/<int:pk>/', CopyVideoCreatorView.as_view()),
    path('image/generate/<int:pk>/', GenerateImageView.as_view()),
    path('image/generate/link/<int:pk>/', GenerateImageLinkView.as_view()),
    path('image/rt-generate/', GenerateImageThumbnailView.as_view()),
    path('template/copy/<int:pk>/', SaveTempleteView.as_view()),
    
]
