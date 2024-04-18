from django.contrib import admin

from externalAssets.models import (
    Icons,Elements,Shapes,
	Mask,Emoji
)

class IconsAdmin(admin.ModelAdmin):
	model = Icons
	list_display = ['name', 'tags',]

class ElementsAdmin(admin.ModelAdmin):
	model = Elements
	list_display = ['name', 'tags',]

class ShapesAdmin(admin.ModelAdmin):
	model = Shapes
	list_display = ['name', 'tags',]


admin.site.register(Icons,IconsAdmin)
admin.site.register(Elements,ElementsAdmin)
admin.site.register(Shapes,ShapesAdmin)
admin.site.register(Mask)
admin.site.register(Emoji)