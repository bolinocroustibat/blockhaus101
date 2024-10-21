from django.db import models


class AiModel(models.Model):
    id = models.CharField("Identifiant du modèle", max_length=32, primary_key=True)

    friendly_name = models.CharField(
        "Nom convivial du modèle",
        max_length=64,
        null=True,
        blank=True,
    )

    supplier = models.CharField(
        "Fournisseur du modèle",
        null=True,
        blank=True,
    )

    max_input_tokens = models.IntegerField(
        "Nombre maximal de tokens en entrée",
        null=True,
        blank=True,
    )

    max_output_tokens = models.IntegerField(
        "Nombre maximal de tokens en sortie",
        null=True,
        blank=True,
    )

    price_input_per_1M = models.FloatField(
        "Prix pour 1M tokens en entrée",
        null=True,
        blank=True,
    )

    price_output_per_1M = models.FloatField(
        "Prix pour 1M tokens en sortie",
        null=True,
        blank=True,
    )

    available = models.BooleanField(
        "Disponible chez le fournisseur",
        default=True,
    )

    active = models.BooleanField(
        "Avtivé manuellement dans l'application",
        default=True,
    )

    added = models.DateTimeField("date d'ajout'", auto_now_add=True)

    modified = models.DateTimeField("date de modification", auto_now=True)

    @property
    def max_input_words(self) -> int | None:
        return round(self.max_input_tokens / 4 * 3) if self.max_input_tokens else None

    @property
    def max_output_words(self) -> int | None:
        return round(self.max_output_tokens / 4 * 3) if self.max_output_tokens else None

    class Meta:
        db_table = "blockhaus101_ai_models"
        verbose_name = "generative AI model"

    def __str__(self) -> str:
        name = self.friendly_name or self.id
        return f"{self.supplier} - {name}"
