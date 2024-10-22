from django.db import models

from base_data_app.models import Language


class ExhibitionTitle(models.Model):
    language = models.ForeignKey(Language, related_name="titles", on_delete=models.PROTECT)
    exhibition = models.ForeignKey("Exhibition", related_name="titles", on_delete=models.CASCADE)
    text = models.CharField("exhibition title", max_length=80)

    class Meta:
        db_table = "blockhaus101_exhibitions_titles"
        unique_together = (
            "language",
            "exhibition",
        )
        verbose_name = "titre d'exposition"
        verbose_name_plural = "titres d'exposition"

    def __str__(self) -> str:
        return f"{self.text} ({self.pk})"
