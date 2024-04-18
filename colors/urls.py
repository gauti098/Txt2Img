from django.urls import path

from colors.views import (
    ColorsView,HealthCheckView
)

urlpatterns = [
    path('', ColorsView.as_view()),
    path('alive/', HealthCheckView.as_view()),
]