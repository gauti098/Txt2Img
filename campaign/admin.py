from django.contrib import admin
from campaign.models import (
    MainCampaign,SoloCampaign,
    GroupSingleCampaign,GroupCampaign,
    EmailClient
)

admin.site.register(MainCampaign)
admin.site.register(SoloCampaign)
admin.site.register(GroupSingleCampaign)
admin.site.register(GroupCampaign)
admin.site.register(EmailClient)
