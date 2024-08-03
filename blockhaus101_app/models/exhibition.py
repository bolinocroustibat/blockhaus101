import re
from datetime import datetime, timedelta
from typing import Self

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import logger
from blockhaus101_app.models.artist import Artist
from blockhaus101_app.models.sitesetting import SiteSetting


class Exhibition(models.Model):
    language = models.ForeignKey(Language, related_name="exhibitions", on_delete=models.PROTECT)
    title = models.CharField("exhibition title", max_length=80)
    artist = models.ForeignKey(Artist, related_name="exhibitions", on_delete=models.PROTECT)
    startdate = models.DateTimeField("exhibition start date", blank=True, null=True)
    enddate = models.DateTimeField("exhibition end date", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_exhibitions"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.startdate or not self.enddate:
            try:
                period = SiteSetting.objects.get().period
            except Exception:
                period = 7
            logger.debug("Trying to save new exhitiion...")
            try:
                self.startdate = Exhibition.objects.latest("enddate").enddate
                self.enddate = self.startdate + timedelta(days=period)
                logger.debug(
                    "AT LEAST ONE EXHIBITION ALREADY PRESENT, EXHIBITION SAVED ACCORDING TO PREVIOUS!"
                )
            except Exception:
                self.startdate = datetime.now()
                self.enddate = datetime.now() + timedelta(days=period)
                logger.debug("NO EXHIBITIONS ALREADY PRESENT, FIRST EXHIBITION TO SAVE!")
        super(Exhibition, self).save(*args, **kwargs)

    def generate(self) -> None:
        title_structures = Data.choose_random(type="expos", language=self.language)
        title = title_structures.text
        title = title.replace("[SELF]", self.artist.name)
        title = title.replace("[SELFDISCIPLINE]", self.artist.discipline_text)
        keywords: list = re.findall(r"\[[^][]*]", title)
        used_words: dict = {}
        for k in keywords:
            word_type = k.replace("[", "").replace("]", "")
            chosen_data = Data.choose_random_excluding(
                type=word_type, language=self.language, excluding=used_words
            )
            if chosen_data:
                chosen_word = chosen_data[0]
                used_words = chosen_data[1]
                # only replace one occurence, we want the same keyword to be able to be replaced by another word
                title = title.replace(f"[{word_type}]", chosen_word, 1)
        logger.debug(f"Used words {used_words} for title")
        self.title = title

    @classmethod
    def get_current(cls, lang: str = "fr") -> Self | None:
        """
        Get the exhibition for the current period
        """
        exhibitions = cls.objects.filter(
            language__lang=lang,
            startdate__lte=datetime.now(),
            enddate__gte=datetime.now(),
        )
        if len(exhibitions) == 0:
            return None
        else:
            return exhibitions[0]
