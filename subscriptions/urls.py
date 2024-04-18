from django.urls import path


from subscriptions.views import (
    CreditDetailsView
)

urlpatterns = [
    path('', CreditDetailsView.as_view())

]