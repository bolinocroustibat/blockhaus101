import asyncio
import unicodedata

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import GENDER_CHOICES, logger
from blockhaus101_app.helpers import OpenAiAPI
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
        return f"{self.name} (pk {self.pk}, gender {self.gender})"

    def generate(self, *args, **kwargs):
        # first name and genre
        firstname = Data.choose_random(data_type="FIRSTNAME")
        if not firstname:
            raise ValueError("Could not find a random first name")
        self.gender = firstname.gender
        # last name
        lastname = Data.choose_random(data_type="LASTNAME")
        if not lastname:
            raise ValueError("Could not find a random last name")
        # full name
        self.name = firstname.text + " " + lastname.text
        # discipline
        self.discipline = Data.choose_random(data_type="DISCIPLINE", lang="en")
        if not self.discipline:
            raise ValueError("Could not find a random discipline")

    def generate_bios(self, expo_titles: dict[str, ExhibitionTitle]) -> dict[str, ArtistBiography]:
        """Generate bios for all languages.
        Returns a dictionary with the language code as key and the ArtistBiography object as value."""
        res: dict = {}
        lg_fr = Language.objects.get(code="fr")
        lg_en = Language.objects.get(code="en")
        # Generate original French biography
        bio_fr = ArtistBiography(artist=self, language=lg_fr)
        bio_fr.generate(expo_title=str(expo_titles[lg_fr.code].text or ""))
        res[lg_fr.code] = bio_fr
        # Translate to English
        openai_api = OpenAiAPI()
        bio_translated, _price, _error_msg = asyncio.run(
            openai_api.translate(
                text=str(bio_fr.text or ""), origin_language=lg_fr, dest_language=lg_en
            )
        )
        # Ensure we have a valid translation
        if not bio_translated or bio_translated.strip() == "":
            logger.error("Translation failed for artist biography. Using French text as fallback.")
            bio_translated = str(bio_fr.text or "")

        bio_en = ArtistBiography(artist=self, language=lg_en, text=bio_translated)
        res[lg_en.code] = bio_en
        return res

    @property
    def name_slug(self) -> str:
        """Convert name to a filesystem-safe slug by normalizing special characters."""
        # Normalize Unicode characters (e.g., ç -> c)
        normalized = unicodedata.normalize("NFKD", self.name)
        # Remove diacritics (accents, etc.)
        ascii_name = "".join(c for c in normalized if not unicodedata.combining(c))
        # Replace spaces with hyphens and convert to lowercase
        return ascii_name.replace(" ", "-").lower()

    def get_discipline(self, lang: str | None = None) -> str:
        if not self.discipline:
            return ""
        if lang:
            if (
                self.discipline.translation
                and self.discipline.translation.language == Language.objects.get(code=lang)
            ):
                return self.discipline.translation.text
            translated_discipline = Data.objects.filter(
                data_type__name="DISCIPLINE", language__code=lang, translation=self.discipline
            ).first()
            if translated_discipline:
                return translated_discipline.text
        return self.discipline.text
