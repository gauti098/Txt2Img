from django.contrib import admin
from salesPage.models import (
    SalesPageEditor,TextEditor,
    ImageEditor,ButtonEditor,
    IconEditor,VideoEditor,CrouselEditor,
    ButtonDataEditor,SalesPageDetails,
    VideoCreatorTracking
)


class SalesPageEditorAdmin(admin.ModelAdmin):
    list_filter = ('isPublic',)




admin.site.register(SalesPageEditor,SalesPageEditorAdmin)
admin.site.register(TextEditor)
admin.site.register(IconEditor)
admin.site.register(ImageEditor)
admin.site.register(ButtonEditor)
admin.site.register(VideoEditor)
admin.site.register(CrouselEditor)
admin.site.register(ButtonDataEditor)
admin.site.register(SalesPageDetails)
admin.site.register(VideoCreatorTracking)