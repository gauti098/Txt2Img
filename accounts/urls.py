from django.urls import path,include
from accounts.views import (
    GoogleSocialAuthView,AccountUser,
    UserOrganization,ManageOrganization,
    OrganizationFetchCode,OrganizationUserRemove,
    ContactUsView,FAQusetionsView,OrganizationUserAdmin,
    EmailGrabView
)

urlpatterns = [
    path('social-auth/google/', GoogleSocialAuthView.as_view()),
    path('user/', AccountUser.as_view()),
    path('user/organization/',UserOrganization.as_view()),
    path('user/organization/add/',ManageOrganization.as_view()),
    path('user/organization/codeverify/',OrganizationFetchCode.as_view()),
    path('user/organization/remove/',OrganizationUserRemove.as_view()),
    path('user/organization/adminchange/',OrganizationUserAdmin.as_view()),
    
    path('contactus/',ContactUsView.as_view()),
    path('faqs/',FAQusetionsView.as_view()),
    path('client/',EmailGrabView.as_view()),

]