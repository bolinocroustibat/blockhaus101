import re
from random import randint, choice

from django.db import models

from blockhaus101_app.helpers.logger import logger
from blockhaus101_app.helpers.string import correct_sentence, unique_slugify
from blockhaus101_app.models.data import Data
from blockhaus101_app.models.exhibition import Exhibition
from blockhaus101_app.models.language import Language


class ExpoText(models.Model):

    language = models.ForeignKey(
        Language, related_name="expotexts", on_delete=models.PROTECT
    )
    text = models.TextField("exhibition text", max_length=3000)
    exhibition = models.ForeignKey(
        Exhibition,
        related_name="expotexts",
        on_delete=models.CASCADE,
        verbose_name="exhibition",
    )
    slug = models.SlugField(
        default=None, null=True, blank=True, max_length=150, verbose_name="URL"
    )
    ip = models.GenericIPAddressField("creator IP address", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.text[:60]

    class Meta:
        db_table = "blockhaus101_expotexts"
        verbose_name = "Exhibition text"
        verbose_name_plural = "Exhibitions texts"

    def save(self, *args, **kwargs) -> None:
        slug_string = "{}-{}".format(self.exhibition.artist.name, self.exhibition.title)
        unique_slugify(
            self, slug_string
        )  # if this slug exists for others, add a number at the end of the slug attribute of the instance
        super(ExpoText, self).save(*args, **kwargs)

    def generate(self, ip: str = None) -> None:
        self.ip = ip
        self.text = ""
        self.used_words = dict()
        if randint(1, 3) == 1:
            self.text = self.create_expo_sentence(position=1)
        self.text = self.text + " " + self.create_expo_sentence(position=2)
        if randint(1, 3) == 1:
            self.text = self.text + " " + self.create_expo_sentence(position=3)
        self.text = self.text + " " + self.create_expo_sentence(position=4)
        self.text = self.text + " " + self.create_expo_sentence(position=5)
        self.text = self.text + " " + self.create_expo_sentence(position=6)
        if self.exhibition.artist.gender == "f":
            self.text = self.text.replace("Il ", "Elle ")
        logger.debug(f"## Exhibition text used words: {self.used_words}")

    def create_expo_sentence(self, position: int = None) -> str:
        structures = Data.objects.filter(type__name="phrases", position=position)
        sentence = choice(structures).text
        sentence = sentence.replace("[SELF]", self.exhibition.artist.name)
        sentence = sentence.replace(
            "[SELFDISCIPLINE]", self.exhibition.artist.discipline
        )
        sentence = sentence.replace("[SELFEXPO]", self.exhibition.title)
        sentence = sentence.replace(
            "[EXPO]", self.exhibition.artist.create_expo_title()
        )
        keywords: list = re.findall(r"\[[^][]*]", sentence)
        for k in keywords:
            word_type = k.replace("[", "").replace("]", "")
            chosen_data = Data.choose_random(
                word_type=word_type, used_words=self.used_words
            )
            if chosen_data:
                chosen_word = chosen_data[0]
                self.used_words = chosen_data[1]
                # only replace one occurence, we want the same keyword to be able to be replaced by another word
                sentence = sentence.replace(f"[{word_type}]", chosen_word, 1)
        sentence = correct_sentence(sentence)
        return sentence
