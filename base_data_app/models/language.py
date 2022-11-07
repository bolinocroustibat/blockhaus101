from django.db import models


class Language(models.Model):
    LANGUAGE_CHOICES = (("en", "English"), ("fr", "French"))
    lang = models.CharField(
        "language code", max_length=2, choices=LANGUAGE_CHOICES, default="fr"
    )

    class Meta:
        db_table = "blockhaus101_languages"

    def __str__(self) -> str:
        return self.lang
