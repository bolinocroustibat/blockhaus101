from django.contrib import admin
from django.contrib.auth.models import Group

from base_data_app.models import *


admin.site.unregister(Group)


@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    model = DataType
    list_display = ("name", "created", "language", "id")
    list_filter = ("language",)
    search_fields = ["name"]


@admin.register(Data)
class DataAdmin(admin.ModelAdmin):
    model = Data
    list_display = ("text", "type", "gender", "weight", "position", "id")
    list_filter = ("type",)
    search_fields = ["text", "type__name"]