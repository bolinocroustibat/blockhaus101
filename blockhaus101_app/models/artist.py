import re
from random import randint, choice

from django.db import models

from blockhaus101_app.helpers import logger, correct_sentence
from blockhaus101_app.models.data import Data
from blockhaus101_app.models.language import Language


class Artist(models.Model):

    language = models.ForeignKey(
        Language, related_name="artists", on_delete=models.PROTECT
    )
    name = models.CharField("artist name", max_length=80)
    GENDER_CHOICES = (("f", "female"), ("m", "male"))
    gender = models.CharField("artist gender", max_length=6, choices=GENDER_CHOICES)
    discipline = models.CharField("artiste discipline", max_length=80)
    bio = models.TextField("artist biography", max_length=2000)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_artists"

    def __str__(self) -> str:
        return self.name

    def generate(self) -> None:
        # first name and genre
        firstnames = Data.objects.filter(type__name="FIRSTNAME")
        firstname = choice(firstnames)
        self.gender = firstname.gender
        # last name
        lastnames = Data.objects.filter(type__name="LASTNAME")
        lastname = choice(lastnames)
        # full name
        self.name = firstname.text + " " + lastname.text
        # discipline
        disciplines = Data.objects.filter(type__name="DISCIPLINE")
        self.discipline = choice(disciplines).text
        # bio
        self.bio_used_words = dict()
        self.bio = self.create_bio_sentence(position=1)
        self.bio = self.bio + " " + self.create_bio_sentence(position=2)
        self.bio = self.bio + " " + self.create_bio_sentence(position=3)
        if randint(1, 3) == 2:
            self.bio = self.bio + " " + self.create_bio_sentence(position=4)
        if self.gender == "f":
            self.bio = self.bio.replace(" il ", " elle ")
            self.bio = self.bio.replace("qu'il ", "qu'elle ")
            self.bio = self.bio.replace("Il ", " Elle ")
            self.bio = self.bio.replace(" né ", " née ")
            self.bio = self.bio.replace("Né ", "Née ")
            self.bio = self.bio.replace("iplômé ", "iplômée ")
            self.bio = self.bio.replace("marqué ", "marquée ")
            self.bio = self.bio.replace("obsédé ", "obsédée ")
        logger.debug(f"## Biography used words: {self.bio_used_words}")

    def create_bio_sentence(self, position: int = None) -> str:
        bio_structures = Data.objects.filter(type__name="bio", position=position)
        biosentence = choice(bio_structures).text
        biosentence = biosentence.replace("[SELF]", self.name)
        biosentence = biosentence.replace("[SELFDISCIPLINE]", self.discipline)
        biosentence = biosentence.replace("[EXPO]", self.create_expo_title())
        keywords: list = re.findall(r"\[[^][]*]", biosentence)
        for k in keywords:
            word_type = k.replace("[", "").replace("]", "")
            chosen_data = Data.choose_random(
                word_type=word_type, used_words=self.bio_used_words
            )
            if chosen_data:
                chosen_word = chosen_data[0]
                self.bio_used_words = chosen_data[1]
                # only replace one occurence, we want the same keyword to be able to be replaced by another word
                biosentence = biosentence.replace(f"[{word_type}]", chosen_word, 1)
        biosentence = correct_sentence(biosentence)
        return biosentence

    def create_expo_title(self) -> str:
        title_structures = Data.objects.filter(type__name="expos")
        title = choice(title_structures).text
        title = title.replace("[SELF]", self.name)
        title = title.replace("[SELFDISCIPLINE]", self.discipline)
        keywords: list = re.findall(r"\[[^][]*]", title)
        used_words = dict()
        for k in keywords:
            word_type = k.replace("[", "").replace("]", "")
            chosen_data = Data.choose_random(word_type=word_type, used_words=used_words)
            if chosen_data:
                chosen_word = chosen_data[0]
                used_words = chosen_data[1]
                # only replace one occurence, we want the same keyword to be able to be replaced by another word
                title = title.replace(f"[{word_type}]", chosen_word, 1)
        logger.debug(f"##  Title used words: {used_words}")
        return title
