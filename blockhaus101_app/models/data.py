from django.db import models

from blockhaus101_app.models.language import Language


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


class Data(models.Model):

    type = models.ForeignKey(DataType, related_name="data", on_delete=models.PROTECT)
    text = models.TextField("data", max_length=3000)
    gender = models.CharField("gender / plural", max_length=8, null=True, blank=True)
    weight = models.IntegerField("weight", null=True, blank=True)
    position = models.IntegerField("position of the sentence in the paragraph", null=True, blank=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.text[:60]

    class Meta:
        db_table = "blockhaus101_data"
