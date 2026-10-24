from django.db import models


class DataType(models.Model):
    name = models.CharField("data type", max_length=80, unique=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        db_table = "blockhaus101_datatype"
        ordering = ("name",)
