from random import choices
from typing import Self

from django.db import models

from base_data_app.models.data_type import DataType
from base_data_app.models.language import Language
from blockhaus101.settings import GENDER_CHOICES, logger


class Data(models.Model):
    data_type = models.ForeignKey(DataType, related_name="data", on_delete=models.CASCADE)
    text = models.TextField("data", max_length=3000)
    language = models.ForeignKey(
        Language,
        related_name="data",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    translation = models.ForeignKey(
        "self",
        related_name="translations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    PLURAL_CHOICES = (
        ("s", "singular"),
        ("p", "plural"),
    )
    plural = models.CharField(max_length=1, choices=PLURAL_CHOICES, null=True, blank=True)
    weight = models.IntegerField("weight", default=10)
    position = models.IntegerField(
        "position of the sentence in the paragraph", null=True, blank=True
    )
    created = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.text[:60]

    class Meta:
        db_table = "blockhaus101_data"
        ordering = ["position"]

    @classmethod
    def choose_random(cls, data_type: str, lang: str | None = None) -> Self | None:
        """
        https://stackoverflow.com/questions/63425139/how-do-i-quickly-get-a-weighted-random-instance-of-a-django-model-instance-based
        """
        entries: models.QuerySet = cls.objects.filter(data_type__name=data_type)
        if lang:
            entries = entries.filter(
                models.Q(language__lang=lang) | models.Q(language=None)
            )  # we choose entries with the right language or no language
        if entries:
            return choices(entries, weights=[e.weight for e in entries])[0]
        return None

    @classmethod
    def choose_random_excluding(
        cls,
        data_type: str,
        lang: str | None = None,
        excluding: list[Self] | None = None,
    ) -> tuple[Self, list[Self]] | None:
        """
        Choose a random entry from the database, according to the type, and to the entries already being used before.
        Args:
            data_type: str: the type of the entry
            language: Language: the language of the entry
            excluding: list: the entries already being used
        Returns:
            tuple: the chosen entry and the updated excluding list, or None.
        """
        chosen_entry: Data | None = cls.choose_random(data_type=data_type, lang=lang)
        if chosen_entry:
            if not excluding:
                # create the forbidden entries array if it doesn't exist
                excluding = []
            else:
                while chosen_entry in excluding:
                    logger.debug(
                        f"entry '{chosen_entry.text}' of type '{data_type}' has been used already, let's choose another"
                    )
                    chosen_entry = cls.choose_random(data_type=data_type, lang=lang)
                    if chosen_entry not in excluding:
                        logger.debug(f"...ok we found another: {chosen_entry.text}")
                        break
            # add the entry to the array of the entry type in the forbidden entries array
            excluding.append(chosen_entry)
            # # TODO
            # try:  # if there is a gender attribute to the data
            #     gender = chosen_entry.gender
            # except:
            #     gender = ""
            return (chosen_entry, excluding)
        return None
