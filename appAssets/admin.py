from django.contrib import admin
from appAssets.models import (
    AvatarImages,AvatarSounds,
    AvatarSoundCombination,
    CountryDetails,VoiceLanguage
)

class CountryDetailsAdmin(admin.ModelAdmin):
    search_fields = ['name', 'code',]

class VoiceLanguageAdmin(admin.ModelAdmin):
    search_fields = ['name', 'code','tags',]


admin.site.register(AvatarSounds)
admin.site.register(AvatarImages)
admin.site.register(AvatarSoundCombination)
admin.site.register(CountryDetails,CountryDetailsAdmin)
admin.site.register(VoiceLanguage,VoiceLanguageAdmin)