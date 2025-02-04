from django.contrib import admin

from blockhaus101.settings import ENVIRONMENT, VERSION
from blockhaus101_app.models import (
    Artist,
    ArtistBiography,
    Exhibition,
    ExhibitionText,
    ExhibitionTitle,
    SiteSetting,
)

admin.AdminSite.site_header = f"galerie Søren Bollinger {VERSION} ({ENVIRONMENT})"
admin.AdminSite.site_title = "galerie Søren Bollinger"
admin.AdminSite.index_title = "Admin main menu"


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    model = SiteSetting
    list_display = ("language",)


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


class ExhibitionTitleAdminInline(admin.TabularInline):
    model = ExhibitionTitle
    extra = 1


class ExhibitionTextAdminInline(admin.TabularInline):
    model = ExhibitionText
    extra = 1
    exclude = ("ip",)
    readonly_fields = ("slug",)


@admin.register(Exhibition)
class ExhibitionAdmin(admin.ModelAdmin):
    model = Exhibition
    list_display = ("get_fr_title", "startdate", "enddate", "created", "id")
    list_filter = ("artist__name",)
    search_fields = ["get_fr_title", "get_en_title", "artist__name"]
    inlines = [ExhibitionTitleAdminInline, ExhibitionTextAdminInline]

    def get_fr_title(self, obj):
        return obj.titles.filter(language__code="fr").first().text

    def get_en_title(self, obj):
        return obj.titles.filter(language__code="en").first().text
