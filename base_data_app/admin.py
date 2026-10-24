from django.contrib import admin
from django.contrib.auth.models import Group

from base_data_app.models import Data, DataType

admin.site.unregister(Group)


@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    model = DataType
    list_display = ("name", "created", "id")
    search_fields = ("name",)


@admin.register(Data)
class DataAdmin(admin.ModelAdmin):
    model = Data
    list_display = (
        "text",
        "data_type",
        "language",
        "translation",
        "gender",
        "plural",
        "weight",
        "position",
        "id",
    )
    list_filter = (
        "language",
        "data_type",
    )
    search_fields = ("text", "data_type__name")
