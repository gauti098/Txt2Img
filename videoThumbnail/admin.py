from django.contrib import admin

from videoThumbnail.models import MainThumbnail,ThumbnailBase64FileUrl

class MainThumbnailAdmin(admin.ModelAdmin):
    list_filter = ('category','isPublic',)

admin.site.register(MainThumbnail,MainThumbnailAdmin)
admin.site.register(ThumbnailBase64FileUrl)