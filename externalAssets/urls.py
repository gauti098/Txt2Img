from externalAssets.models import Elements
from django.urls import path

from externalAssets.views import (
    IconsView,ShapesView,ElementsView,
    MaskView,EmojiView,CommonView
)


urlpatterns = [
    path('shapes/', ShapesView.as_view()),
    path('icons/', IconsView.as_view()),
    path('elements/', ElementsView.as_view()),
    path('emoji/', EmojiView.as_view()),
    path('common/', CommonView.as_view()),
    path('masks/', MaskView.as_view()),

]
