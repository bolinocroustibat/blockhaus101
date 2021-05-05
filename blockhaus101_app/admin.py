from django.contrib import admin
from .models import *


class SiteSettingAdmin(admin.ModelAdmin):
	model = SiteSetting
admin.site.register(SiteSetting, SiteSettingAdmin)

class ExhibitionAdmin(admin.ModelAdmin):
	model = Exhibition
admin.site.register(Exhibition, ExhibitionAdmin)

class ArtistAdmin(admin.ModelAdmin):
	model = Artist
admin.site.register(Artist, ArtistAdmin)

class ExpoTextAdmin(admin.ModelAdmin):
	model = ExpoText
admin.site.register(ExpoText, ExpoTextAdmin)
