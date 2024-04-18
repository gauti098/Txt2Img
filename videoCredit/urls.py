from django.urls import path

from videoCredit.views import (
    CreditInfoView,CreditDetailsInfoView
)

urlpatterns = [
    path('info/', CreditInfoView.as_view()),
    path('details/', CreditDetailsInfoView.as_view()),
]