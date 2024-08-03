import re
from random import choice, randint

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import correct_sentence


class Artist(models.Model):
    language = models.ForeignKey(Language, related_name="artists", on_delete=models.PROTECT)
    name = models.CharField("artist name", max_length=80)
    GENDER_CHOICES = (("f", "female"), ("m", "male"))
    gender = models.CharField("artist gender", max_length=6, choices=GENDER_CHOICES)
    discipline = models.ForeignKey(Data, related_name="artists", on_delete=models.PROTECT)
    bio = models.TextField("artist biography", max_length=2000)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_artists"

    def __str__(self) -> str:
        return self.name

    @property
    def discipline_text(self) -> str:
        if self.language == self.discipline.language:
            return self.discipline.text
        if not self.discipline.translation:
            logger.error("No translation for discipline")
            return self.discipline.text
        return self.discipline.translation.text

    def _generate_name(self) -> None:
        # first name and genre
        firstname = Data.choose_random(type="FIRSTNAME", language=self.language)
        self.gender = firstname.gender
        # last name
        lastname = Data.choose_random(type="LASTNAME", language=self.language)
        # full name
        self.name = firstname.text + " " + lastname.text

    def generate(self) -> None:
        self._generate_name()
        # discipline
        self.discipline = Data.choose_random(type="DISCIPLINE")

    def _generate_biography(self) -> None:
        self.bio_used_words: dict = {}
        self.bio = self._generate_bio_sentence(position=1)
        self.bio = self.bio + " " + self._generate_bio_sentence(position=2)
        self.bio = self.bio + " " + self._generate_bio_sentence(position=3)
        if randint(1, 3) == 2:
            self.bio = self.bio + " " + self._generate_bio_sentence(position=4)
        if self.gender == "f":
            self.bio = self.bio.replace(" il ", " elle ")
            self.bio = self.bio.replace("qu'il ", "qu'elle ")
            self.bio = self.bio.replace("Il ", " Elle ")
            self.bio = self.bio.replace(" né ", " née ")
            self.bio = self.bio.replace("Né ", "Née ")
            self.bio = self.bio.replace("iplômé ", "iplômée ")
            self.bio = self.bio.replace("marqué ", "marquée ")
            self.bio = self.bio.replace("obsédé ", "obsédée ")
        logger.debug(f"Biography used words: {self.bio_used_words}")

    def _generate_bio_sentence(self, position: int) -> str:
        bio_structures = Data.objects.filter(
            language=self.language, type__name="bio", position=position
        )
        biosentence = choice(bio_structures).text
        biosentence = biosentence.replace("[SELF]", self.name)
        biosentence = biosentence.replace("[SELFDISCIPLINE]", self.discipline_text)
        keywords: list = re.findall(r"\[[^][]*]", biosentence)
        for k in keywords:
            if k == "[EXPO]":
                # only replace one occurence, we want the same keyword to be able to be replaced by other words
                biosentence = biosentence.replace("[EXPO]", self.generate_expo_title(), 1)
            else:
                word_type = k.replace("[", "").replace("]", "")
                chosen_data = Data.choose_random_excluding(
                    type=word_type,
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
