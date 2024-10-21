from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import GENDER_CHOICES, logger


class Artist(models.Model):
    name = models.CharField("artist name", max_length=80)
    gender = models.CharField("artist gender", max_length=6, choices=GENDER_CHOICES)
    discipline = models.ForeignKey(Data, related_name="artists", on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_artists"
        verbose_name = "artiste"

    def __str__(self) -> str:
        return f"{self.name} ({self.pk})"

    def generate(self, *args, **kwargs):
        # first name and genre
        firstname = Data.choose_random(data_type="FIRSTNAME")
        self.gender = firstname.gender
        # last name
        lastname = Data.choose_random(data_type="LASTNAME")
        # full name
        self.name = firstname.text + " " + lastname.text
        # discipline
        self.discipline = Data.choose_random(
            data_type="DISCIPLINE", language=Language.objects.get(lang="en")
        )

    @property
    def name_slug(self) -> str:
        return self.name.replace(" ", "-").lower()

    def discipline_text(self, language: Language | None = None) -> str:
        if language:
            if self.discipline.translation.language == language:
                return self.discipline.translation.text
            else:
                translated_discipline = Data.objects.filter(
                    data_type__name="DISCIPLINE", language=language, translation=self.discipline
                ).first()
                if translated_discipline:
                    return translated_discipline.text
            logger.warning(
                f'No translation for discipline {self.discipline.pk} ("{self.discipline.text}")'
            )
        return self.discipline.text
