from django.contrib import admin
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from newVideoCreator.models import (
    TempVideoCreator,VideoAnimation,
    VideoFilter,VideoTemplate,
    MainVideoGenerate,VideoSceneAnimation,
    TextAnimation,AiVideoSceneGenerate,FontConfig,
    FontFamily,AiTaskWithAudio,GroupHandler,
    EmailGenTracker,VideoEditorHistoryMaintainer
)



class AiTaskWithAudioAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_filter = ('status',)


class MainVideoGenerateAdmin(admin.ModelAdmin):
    list_filter = ('generationType','status',)

class VideoEditorHistoryMaintainerAdmin(admin.ModelAdmin):
    model = VideoEditorHistoryMaintainer
    readonly_fields = ('timestamp',)
    list_filter = ('status',)
    list_display = ['videoCreator', 'status', 'timestamp',]
	

        
admin.site.register(AiTaskWithAudio,AiTaskWithAudioAdmin)
admin.site.register(MainVideoGenerate,MainVideoGenerateAdmin)
admin.site.register(VideoEditorHistoryMaintainer,VideoEditorHistoryMaintainerAdmin)

admin.site.register(TempVideoCreator)
admin.site.register(EmailGenTracker)
admin.site.register(VideoTemplate)

admin.site.register(VideoAnimation)
admin.site.register(TextAnimation)
admin.site.register(VideoSceneAnimation)
admin.site.register(VideoFilter)
admin.site.register(AiVideoSceneGenerate)
admin.site.register(GroupHandler)

#admin.site.register(AiTaskWithAudio)

admin.site.register(FontConfig)
admin.site.register(FontFamily)
