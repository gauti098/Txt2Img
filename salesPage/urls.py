from django.urls import path,include
from salesPage.views import (
    SalesPageDetailView,SalesPageTemplateView,
    SalesPageCopyView,SalesPagePublicTemplateView,
    SalesPageDetailsView,SalesPagePublicIdView
)

urlpatterns = [
    path('<int:pk>/', SalesPageDetailView.as_view()),
    path('public/<int:pk>/', SalesPagePublicIdView.as_view()),
    path('public/', SalesPagePublicTemplateView.as_view()),
    path('<int:pk>/copy/', SalesPageCopyView.as_view()),
    path('', SalesPageTemplateView.as_view()),

    path('<int:pk>/details/', SalesPageDetailsView.as_view()),

]