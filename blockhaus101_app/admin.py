from django.contrib import admin

from blockhaus101.settings import ENVIRONMENT, VERSION
from blockhaus101_app.models import Artist, Exhibition, ExpoText, SiteSetting

admin.AdminSite.site_header = f"Blockhaus101 {VERSION} ({ENVIRONMENT})"
admin.AdminSite.site_title = "Blockhaus101"
admin.AdminSite.index_title = "Admin main menu"


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    model = SiteSetting
    list_display = ("language", "period")


@admin.register(Exhibition)
class ExhibitionAdmin(admin.ModelAdmin):
    model = Exhibition
    list_display = ("title", "startdate", "enddate", "created", "language", "id")
    list_filter = ("language", "artist__name")
    search_fields = ["title", "artist__name"]


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    model = Artist
    list_display = ("name", "gender", "discipline", "created", "language", "id")
    list_filter = ("language",)
    search_fields = ["name", "discipline", "gender"]


@admin.register(ExpoText)
class ExpoTextAdmin(admin.ModelAdmin):
    model = ExpoText
    list_display = ("text", "exhibition", "slug", "ip", "created", "language", "id")
    list_filter = ("language", "ip")
    search_fields = ["text"]
