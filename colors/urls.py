from django.urls import path

from colors.views import (
    ColorsView,HealthCheckView,
    CombineView
)

urlpatterns = [
    path('', ColorsView.as_view()),
    path('combine/', CombineView.as_view()),
    path('alive/', HealthCheckView.as_view()),
]