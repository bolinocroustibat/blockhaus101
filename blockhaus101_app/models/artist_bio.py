import re
from random import choice, randint

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import correct_text
from blockhaus101_app.models.exhibition import Exhibition


class ArtistBiography(models.Model):
    language = models.ForeignKey(Language, related_name="biographies", on_delete=models.PROTECT)
    artist = models.ForeignKey("Artist", related_name="biographies", on_delete=models.CASCADE)
    text = models.TextField("artist biography", max_length=2000)

    def __str__(self) -> str:
        return f"{self.text[:20]} ({self.pk})"

    class Meta:
        db_table = "blockhaus101_artists_biographies"
        unique_together = (
            "language",
            "artist",
        )
        verbose_name = "biographie d'artiste"
        verbose_name_plural = "biographies d'artiste"

    def generate(self, expo_title: str) -> str:
        """
        Generate a biography for the artist in the current language.
        Args:
            expo_title (str): the title of the current exhibition
        Returns:
            str: the artist biography
        """
        self.text_used_data: list = []
        self.text = self._generate_bio_sentence(position=1, expo_title=expo_title)
        self.text = self.text + " " + self._generate_bio_sentence(position=2, expo_title=expo_title)
        self.text = self.text + " " + self._generate_bio_sentence(position=3, expo_title=expo_title)
        if randint(1, 3) == 2:
            self.text = (
                self.text + " " + self._generate_bio_sentence(position=4, expo_title=expo_title)
            )
        logger.debug(f"Used words for artist biography: {self.text_used_data}")
        return self.text

    def _generate_bio_sentence(self, position: int, expo_title: str) -> str:
        bio_structures = Data.objects.filter(
            language=self.language, data_type__name="bio", position=position
        )
        biosentence = choice(bio_structures).text
        biosentence = biosentence.replace("[SELF]", self.artist.name)
        biosentence = biosentence.replace(
            "[SELFDISCIPLINE]", self.artist.get_discipline(lang=self.language.code)
        )
        biosentence = biosentence.replace("[SELFEXPO]", expo_title)
        keywords: list = re.findall(r"\[[^][]*]", biosentence)
        for k in keywords:
            if k == "[EXPO]":
                exhibition = Exhibition(artist=self.artist)
                biosentence = biosentence.replace(
                    "[EXPO]", exhibition.random_title_text(self.language.code), 1
                )
            else:
                word_type = k.replace("[", "").replace("]", "")
                chosen_data = Data.choose_random_excluding(
                    data_type=word_type,
                    lang=self.language.code,
                    excluding=self.text_used_data,
                )
                if chosen_data:
                    chosen_word = chosen_data[0].text
                    self.text_used_data = chosen_data[1]
                    # only replace one occurence, we want the same keyword to be able to be replaced by other words
                    biosentence = biosentence.replace(k, chosen_word, 1)
        biosentence = correct_text(
            text=biosentence, lang=self.language.code, subject_gender=self.artist.gender
        )
        return biosentence
