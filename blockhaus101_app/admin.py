from django.contrib import admin
from .models import *

# Register your models here.

class ArtistAdmin(admin.ModelAdmin):
	model = Artist
admin.site.register(Artist, ArtistAdmin)

class ExpoTitleAdmin(admin.ModelAdmin):
	model = ExpoTitle
admin.site.register(ExpoTitle, ExpoTitleAdmin)

class ExpoTextAdmin(admin.ModelAdmin):
	model = ExpoText
admin.site.register(ExpoText, ExpoTextAdmin)