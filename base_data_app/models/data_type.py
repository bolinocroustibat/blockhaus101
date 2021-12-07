from django.db import models

from base_data_app.models.language import Language


class DataType(models.Model):

    language = models.ForeignKey(
        Language, related_name="data_type", on_delete=models.PROTECT
    )
    name = models.CharField("data type", max_length=80, unique=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        db_table = "blockhaus101_datatype"
        ordering = ["name"]
