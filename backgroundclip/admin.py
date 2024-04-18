from django.contrib import admin
from backgroundclip.models import (
    ImageSearch,ImageApiRes,
    VideoApiRes,VideoSearch,
    APISaveVideo,APIVideoQuerySaver,
    APIVideoPopularSaver,APISaveImage,
    APIImagePopularSaver,APIImageQuerySaver
)

class VideoApiResAdmin(admin.ModelAdmin):
    list_filter = ('is_save',)

class APISaveVideoAdmin(admin.ModelAdmin):
    list_filter = ('apiVideoInstType','isTransparent','isVideoProcessed',)

class APISaveImageAdmin(admin.ModelAdmin):
    list_filter = ('apiVideoInstType','isProcessed',)


admin.site.register(VideoApiRes,VideoApiResAdmin)
admin.site.register(APISaveVideo,APISaveVideoAdmin)
admin.site.register(APISaveImage,APISaveImageAdmin)

admin.site.register(ImageSearch)
admin.site.register(ImageApiRes)
admin.site.register(VideoSearch)
admin.site.register(APIVideoQuerySaver)
admin.site.register(APIVideoPopularSaver)
admin.site.register(APIImagePopularSaver)
admin.site.register(APIImageQuerySaver)