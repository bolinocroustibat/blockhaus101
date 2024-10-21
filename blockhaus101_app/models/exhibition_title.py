import re

from django.db import models

from base_data_app.models import Data, Language
from blockhaus101.settings import logger


class ExhibitionTitle(models.Model):
    language = models.ForeignKey(Language, related_name="titles", on_delete=models.PROTECT)
    exhibition = models.ForeignKey("Exhibition", related_name="titles", on_delete=models.CASCADE)
    text = models.CharField("exhibition title", max_length=80)

    class Meta:
        db_table = "blockhaus101_exhibitions_titles"
        unique_together = (
            "language",
            "exhibition",
        )
        verbose_name = "titre d'exposition"
        verbose_name_plural = "titres d'exposition"

    def __str__(self) -> str:
        return f"{self.text} ({self.pk})"

    def create(self, *args, **kwargs):
        super(ExhibitionTitle, self).__init__(*args, **kwargs)
        language = Language.objects.get(
            lang="fr"
        )  # default language. #TODO: generate titles for both languages
        title_structures = Data.choose_random(data_type="expos", language=language)
        title = title_structures.text
        title = title.replace("[SELF]", self.exhibition.artist.name)
        title = title.replace("[SELFDISCIPLINE]", self.exhibition.artist.discipline_text())
        keywords: list = re.findall(r"\[[^][]*]", title)
        used_words: dict = {}
        for k in keywords:
            word_type = k.replace("[", "").replace("]", "")
            chosen_data = Data.choose_random_excluding(
                data_type=word_type, language=language, excluding=used_words
            )
            if chosen_data:
                chosen_word = chosen_data[0]
                used_words = chosen_data[1]
                # only replace one occurence, we want the same keyword to be able to be replaced by another word
                title = title.replace(f"[{word_type}]", chosen_word, 1)
        logger.debug(f"Used words for exhibition title: {used_words}")
