from random import choice, choices
from typing import Self

from django.db import models

from base_data_app.models.data_type import DataType
from base_data_app.models.language import Language
from blockhaus101.settings import logger


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
    GENDER_CHOICES = (
        ("m", "male"),
        ("f", "female"),
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
    def choose_random(cls, data_type: str, language: Language | None = None) -> Self | None:
        """
        https://stackoverflow.com/questions/63425139/how-do-i-quickly-get-a-weighted-random-instance-of-a-django-model-instance-based
        """
        entries: models.QuerySet = cls.objects.filter(data_type__name=data_type)
        if language:
            entries = entries.filter(
                models.Q(language=language) | models.Q(language=None)
            )  # we choose entries with the right language or no language
        if entries:
            return choices(entries, weights=[e.weight for e in entries])[0]
        return None

    @classmethod
    def choose_random_excluding(
        cls,
        data_type: str,
        language: Language | None = None,
        excluding: dict | None = None,
    ) -> tuple[str, dict] | None:
        """
        Choose a random entry from the database, according to the type, and to the entries already being used before.
        """
        chosen_entry: Data | None = cls.choose_random(data_type=data_type, language=language)
        if chosen_entry:
            if not excluding:
                excluding = {}
            if excluding.get(data_type):
                while chosen_entry.text in excluding[data_type]:
                    logger.debug(
                        f"entry '{chosen_entry.text}' of type '{data_type}' has been used already, let's choose another"
                    )
                    chosen_entry = cls.choose_random(data_type=data_type, language=language)
                    if chosen_entry not in excluding[data_type]:
                        logger.debug(f"...ok we found another: {chosen_entry.text}")
                        break
            else:
                # create the forbidden entries type array for this type of entry if it doesn't exist
                excluding[data_type] = list()
            entry = chosen_entry.text  # store the chosen entry
            # add the entry to the array of the entry type in the forbidden entries array
            excluding[data_type].append(entry)
            # # TODO
            # try:  # if there is a gender attribute to the data
            #     gender = chosen_entry.gender
            # except:
            #     gender = ""
            return (entry, excluding)
        return None
