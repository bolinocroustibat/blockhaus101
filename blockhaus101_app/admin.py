from django.contrib import admin
from django.contrib.auth.models import Group

from blockhaus101_app.models import *


# admin.site.unregister(Group)


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    model = SiteSetting


@admin.register(Exhibition)
class ExhibitionAdmin(admin.ModelAdmin):
    model = Exhibition


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    model = Artist


@admin.register(ExpoText)
class ExpoTextAdmin(admin.ModelAdmin):
    model = ExpoText


@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    model = DataType


@admin.register(Data)
class DataAdmin(admin.ModelAdmin):
    model = Data
