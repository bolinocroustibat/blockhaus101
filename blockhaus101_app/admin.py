from django.contrib import admin

from blockhaus101.settings import ENVIRONMENT, VERSION
from blockhaus101_app.models import Artist, ArtistBiography, Exhibition, ExpoText, SiteSetting

admin.AdminSite.site_header = f"Blockhaus101 {VERSION} ({ENVIRONMENT})"
admin.AdminSite.site_title = "Blockhaus101"
admin.AdminSite.index_title = "Admin main menu"


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    model = SiteSetting
    list_display = ("language", "period")


class ArtistBioAdminInline(admin.TabularInline):
    model = ArtistBiography
    extra = 1


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    model = Artist
    list_display = ("name", "gender", "discipline", "created", "id")
    list_filter = ("gender",)
    search_fields = ["name", "discipline", "gender"]
    inlines = [ArtistBioAdminInline]


class ExpoTextAdminInline(admin.TabularInline):
    model = ExpoText
    extra = 1
    exclude = ("ip",)
    readonly_fields = ("slug",)


@admin.register(Exhibition)
class ExhibitionAdmin(admin.ModelAdmin):
    model = Exhibition
    list_display = ("title", "startdate", "enddate", "created", "id")
    list_filter = ("artist__name",)
    search_fields = ["title", "artist__name"]
    inlines = [ExpoTextAdminInline]
