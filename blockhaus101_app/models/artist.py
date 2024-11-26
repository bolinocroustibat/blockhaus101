from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import GENDER_CHOICES
from blockhaus101_app.models.artist_bio import ArtistBiography
from blockhaus101_app.models.exhibition_title import ExhibitionTitle


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
        self.discipline = Data.choose_random(data_type="DISCIPLINE", lang="en")

    def generate_bios(self, expo_titles: dict[str, ExhibitionTitle]) -> dict[str, ArtistBiography]:
        """Generate bios for all languages.
        Returns a dictionary with the language code as key and the ArtistBiography object as value."""
        res: dict = {}
        for lg in Language.objects.all():
            expo_title = expo_titles[lg.code].text
            bio = ArtistBiography(artist=self, language=lg)
            bio.generate(expo_title=expo_title)
            res[lg.code] = bio
        return res

    @property
    def name_slug(self) -> str:
        return self.name.replace(" ", "-").lower()

    def get_discipline(self, lang: str | None = None) -> str:
        if lang:
            if self.discipline.translation:
                if self.discipline.translation.language == Language.objects.get(code=lang):
                    return self.discipline.translation.text
            translated_discipline = Data.objects.filter(
                data_type__name="DISCIPLINE", language__code=lang, translation=self.discipline
            ).first()
            if translated_discipline:
                return translated_discipline.text
        return self.discipline.text
