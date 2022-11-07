from django.contrib import admin
from django.contrib.auth.models import Group

from base_data_app.models import *


admin.site.unregister(Group)


@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    model = DataType
    list_display = ("name", "created", "id")
    search_fields = ["name"]


@admin.register(Data)
class DataAdmin(admin.ModelAdmin):
    model = Data
    list_display = (
        "text",
        "type",
        "language",
        "gender",
        "plural",
        "weight",
        "position",
        "id",
    )
    list_filter = (
        "language",
        "type",
    )
    search_fields = ["text", "type__name"]
