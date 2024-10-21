import re
from random import choice, randint

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import correct_sentence


class ArtistBiography(models.Model):
    language = models.ForeignKey(Language, related_name="artists", on_delete=models.PROTECT)
    artist = models.ForeignKey("Artist", related_name="biographies", on_delete=models.CASCADE)
    bio = models.TextField("artist biography", max_length=2000)

    def __str__(self) -> str:
        return f"{self.artist.name} ({self.language.lang})"

    class Meta:
        db_table = "blockhaus101_artists_biographies"
        unique_together = (
            "language",
            "artist",
        )
        verbose_name = "biographie d'artiste"
        verbose_name_plural = "biographies d'artiste"

    def generate(self, expo_title: str, save: bool = True) -> None:
        self.bio_used_words: dict = {}
        self.bio = self._generate_bio_sentence(position=1, expo_title=expo_title)
        self.bio = self.bio + " " + self._generate_bio_sentence(position=2, expo_title=expo_title)
        self.bio = self.bio + " " + self._generate_bio_sentence(position=3, expo_title=expo_title)
        if randint(1, 3) == 2:
            self.bio = (
                self.bio + " " + self._generate_bio_sentence(position=4, expo_title=expo_title)
            )
        if self.artist.gender == "f":
            self.bio = self.bio.replace(" il ", " elle ")
            self.bio = self.bio.replace("qu'il ", "qu'elle ")
            self.bio = self.bio.replace("Il ", " Elle ")
            self.bio = self.bio.replace(" né ", " née ")
            self.bio = self.bio.replace("Né ", "Née ")
            self.bio = self.bio.replace("iplômé ", "iplômée ")
            self.bio = self.bio.replace("marqué ", "marquée ")
            self.bio = self.bio.replace("obsédé ", "obsédée ")
        logger.debug(f"Used words for artist biography: {self.bio_used_words}")
        if save:
            self.save()

    def _generate_bio_sentence(self, position: int, expo_title: str) -> str:
        bio_structures = Data.objects.filter(
            language=self.language, data_type__name="bio", position=position
        )
        biosentence = choice(bio_structures).text
        biosentence = biosentence.replace("[SELF]", self.artist.name)
        biosentence = biosentence.replace("[SELFDISCIPLINE]", self.artist.discipline_text())
        keywords: list = re.findall(r"\[[^][]*]", biosentence)
        for k in keywords:
            if k == "[EXPO]":
                # only replace one occurence, we want the same keyword to be able to be replaced by other words
                biosentence = biosentence.replace("[EXPO]", expo_title, 1)
            else:
                word_type = k.replace("[", "").replace("]", "")
                chosen_data = Data.choose_random_excluding(
                    data_type=word_type,
                    language=self.language,
                    excluding=self.bio_used_words,
                )
                if chosen_data:
                    chosen_word = chosen_data[0]
                    self.bio_used_words = chosen_data[1]
                    # only replace one occurence, we want the same keyword to be able to be replaced by other words
                    biosentence = biosentence.replace(k, chosen_word, 1)
        biosentence = correct_sentence(lang=self.language.lang, sentence=biosentence)
        return biosentence
