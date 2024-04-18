from django.contrib.admin import SimpleListFilter
from django.contrib import admin
from campaignAnalytics.models import (
    CampaignGroupAnalytics,CampaignSingleAnalytics,
    CombinedAnalytics,CampaignProspect,CampaignEmailOpenedAnalytics,
    CampaignVideoPlayedAnalytics,CampaignOpenAnalytics,CampaignSentAnalytics,
    CampaignCtaClickedtAnalytics,CampaignCollateralClickedtAnalytics
)




class CampaignFilter(SimpleListFilter):
    title = 'campaign' # or use _('country') for translated title
    parameter_name = 'campaign'

    def lookups(self, request, model_admin):
        return [('campaign', 'All')]

    def queryset(self, request, queryset):
        if self.value():
            if self.value()=='All':
                return queryset.filter(campaign__pk=self.value())
        return queryset

class CampaignProspectAdmin(admin.ModelAdmin):
    list_filter = (CampaignFilter,)

admin.site.register(CampaignProspect,CampaignProspectAdmin)


admin.site.register(CampaignSingleAnalytics)
admin.site.register(CampaignGroupAnalytics)
admin.site.register(CombinedAnalytics)
admin.site.register(CampaignEmailOpenedAnalytics)
admin.site.register(CampaignVideoPlayedAnalytics)
admin.site.register(CampaignOpenAnalytics)
admin.site.register(CampaignSentAnalytics)
admin.site.register(CampaignCtaClickedtAnalytics)
admin.site.register(CampaignCollateralClickedtAnalytics)