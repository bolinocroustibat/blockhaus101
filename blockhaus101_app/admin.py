from django.contrib import admin
from .models import *


class SiteSettingsAdmin(admin.ModelAdmin):
	model = SiteSettings
admin.site.register(SiteSettings, SiteSettingsAdmin)

class ExhibitionAdmin(admin.ModelAdmin):
	model = Exhibition
admin.site.register(Exhibition, ExhibitionAdmin)

class ArtistAdmin(admin.ModelAdmin):
	model = Artist
admin.site.register(Artist, ArtistAdmin)

class ExpoTextAdmin(admin.ModelAdmin):
	model = ExpoText
admin.site.register(ExpoText, ExpoTextAdmin)
