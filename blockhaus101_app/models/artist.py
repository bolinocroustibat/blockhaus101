import re
from random import choice, randint

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import GENDER_CHOICES, logger
from blockhaus101_app.helpers import correct_sentence


class Artist(models.Model):
    language = models.ForeignKey(Language, related_name="artists", on_delete=models.PROTECT)
    name = models.CharField("artist name", max_length=80)
    gender = models.CharField("artist gender", max_length=6, choices=GENDER_CHOICES)
    discipline = models.ForeignKey(Data, related_name="artists", on_delete=models.PROTECT)
    bio = models.TextField("artist biography", max_length=2000)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_artists"

    def __str__(self) -> str:
        return f"{self.name}, {self.gender}, {self.discipline}.\n{self.bio}"

    @property
    def name_slug(self) -> str:
        return self.name.replace(" ", "-").lower()

    @property
    def discipline_text(self, lang: str | None = None) -> str:
        if lang:
            try:
                language = Language.objects.get(lang=lang)
            except Language.DoesNotExist:
                logger.error(f"Language {lang} doesn't exist")
            else:
                try:
                    translated_discipline = Data.objects.filter(
                        type="DISCIPLINE", language=language, translation=self.discipline
                    ).first()
                    return translated_discipline.text
                except Data.DoesNotExist:
                    logger.error(
                        f'No translation for discipline {self.discipline.pk} ("{self.discipline.text}")'
                    )
        return self.discipline.text

    def _generate_name(self) -> None:
        # first name and genre
        firstname = Data.choose_random(data_type="FIRSTNAME", language=self.language)
        self.gender = firstname.gender
        # last name
        lastname = Data.choose_random(data_type="LASTNAME", language=self.language)
        # full name
        self.name = firstname.text + " " + lastname.text

    def generate(self) -> None:
        self._generate_name()
        self.discipline = Data.choose_random(data_type="DISCIPLINE", language=self.language)

    def generate_biography(self, expo_title: str) -> None:
        self.bio_used_words: dict = {}
        self.bio = self._generate_bio_sentence(position=1, expo_title=expo_title)
        self.bio = self.bio + " " + self._generate_bio_sentence(position=2, expo_title=expo_title)
        self.bio = self.bio + " " + self._generate_bio_sentence(position=3, expo_title=expo_title)
        if randint(1, 3) == 2:
            self.bio = (
                self.bio + " " + self._generate_bio_sentence(position=4, expo_title=expo_title)
            )
        if self.gender == "f":
            self.bio = self.bio.replace(" il ", " elle ")
            self.bio = self.bio.replace("qu'il ", "qu'elle ")
            self.bio = self.bio.replace("Il ", " Elle ")
            self.bio = self.bio.replace(" né ", " née ")
            self.bio = self.bio.replace("Né ", "Née ")
            self.bio = self.bio.replace("iplômé ", "iplômée ")
            self.bio = self.bio.replace("marqué ", "marquée ")
            self.bio = self.bio.replace("obsédé ", "obsédée ")
        logger.debug(f"Used words for artist biography: {self.bio_used_words}")

    def _generate_bio_sentence(self, position: int, expo_title: str) -> str:
        bio_structures = Data.objects.filter(
            language=self.language, data_type__name="bio", position=position
        )
        biosentence = choice(bio_structures).text
        biosentence = biosentence.replace("[SELF]", self.name)
        biosentence = biosentence.replace("[SELFDISCIPLINE]", self.discipline_text)
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
