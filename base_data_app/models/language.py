from django.db import models


class Language(models.Model):
    LANGUAGE_CHOICES = ("en", "fr")
    code = models.CharField("language code", max_length=2, choices=LANGUAGE_CHOICES, default="fr")
    name = models.CharField("language name", max_length=20)

    class Meta:
        db_table = "blockhaus101_languages"

    def __str__(self) -> str:
        return self.name
