from django.contrib import admin
from .models import *

# Register your models here.

class ExhibitionAdmin(admin.ModelAdmin):
	model = Exhibition
admin.site.register(Exhibition, ExhibitionAdmin)

class ArtistAdmin(admin.ModelAdmin):
	model = Artist
admin.site.register(Artist, ArtistAdmin)

class ExpoTextAdmin(admin.ModelAdmin):
	model = ExpoText
admin.site.register(ExpoText, ExpoTextAdmin)