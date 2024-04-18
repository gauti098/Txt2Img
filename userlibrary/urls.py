from django.urls import path,include
from userlibrary.views import (
    FileUploadView,FileUploadDetailView,
    ResetDashBoardView
)

urlpatterns = [
    path('upload/', FileUploadView.as_view()),
    path('upload/<int:pk>/', FileUploadDetailView.as_view()),
    path('resetDashboard/', ResetDashBoardView.as_view()),

]