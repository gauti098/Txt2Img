from django.urls import path

from paymentHandler.views import (
    stripe_webhook,StripSessionIdView
)
urlpatterns = [
    path('stripe/webhook/', stripe_webhook),
    path('stripe/create-session/', StripSessionIdView.as_view()),
]