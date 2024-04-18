from django.contrib import admin
from aiQueueManager.models import (
    AiTask,Colors, MergeTag,
    VideoRenderSingleScene,
    VideoRenderMultipleScene,
    GeneratedFinalVideo,SnapshotUrl,
    VideoThemeTemplate,VideoGradientColor
    )

class GeneratedFinalVideoAdmin(admin.ModelAdmin):
    list_filter = ('status',)

class AiTaskAdmin(admin.ModelAdmin):
    list_filter = ('status',)


admin.site.register(GeneratedFinalVideo,GeneratedFinalVideoAdmin)

admin.site.register(AiTask,AiTaskAdmin)
admin.site.register(Colors)
admin.site.register(MergeTag)
admin.site.register(VideoRenderSingleScene)
admin.site.register(VideoRenderMultipleScene)


admin.site.register(SnapshotUrl)
admin.site.register(VideoThemeTemplate)
admin.site.register(VideoGradientColor)