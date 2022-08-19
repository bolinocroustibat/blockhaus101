from random import choice, choices
from typing import Optional

from django.db import models

from blockhaus101.settings import logger
from base_data_app.models.data_type import DataType


class Data(models.Model):

    type = models.ForeignKey(DataType, related_name="data", on_delete=models.CASCADE)
    text = models.TextField("data", max_length=3000)
    GENDER_CHOICES = (
        ("m", "male"),
        ("f", "female"),
    )
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, null=True, blank=True
    )
    PLURAL_CHOICES = (
        ("s", "singular"),
        ("p", "plural"),
    )
    plural = models.CharField(
        max_length=1, choices=PLURAL_CHOICES, null=True, blank=True
    )
    weight = models.IntegerField("weight", null=True, blank=True)
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
    def choose_random(cls, type: str, lang: Optional[str] = None) -> Optional[str]:
        """
        https://stackoverflow.com/questions/63425139/how-do-i-quickly-get-a-weighted-random-instance-of-a-django-model-instance-based
        """
        if lang:
            entries = cls.objects.filter(type__name=type, type__language__lang=lang)
        else:
            entries = cls.objects.filter(type__name=type)
        if entries:
            if not [e for e in entries if e.weight]:
                # if there are some no weighted entries, return a random entry
                return choice(entries)
            else:
                # entries are all weighted, so we can use random.choices
                return choices(entries, weights=[e.weight for e in entries])[0]
        return None

    @classmethod
    def choose_random_excluding(
        cls, type: str, lang: Optional[str], excluding: Optional[dict] = None
    ) -> Optional[tuple[str, dict]]:
        """
        Choose a random entry from the database, according to the type, and to the entries already being used before.
        """
        chosen_entry = cls.choose_random(type=type, lang=lang)
        if chosen_entry:
            if excluding.get(type):
                while chosen_entry.text in excluding[type]:
                    logger.debug(
                        f"entry '{chosen_entry.text}' of type '{type}' has been used already, let's choose another"
                    )
                    chosen_entry = cls.choose_random(type=type)
                    if chosen_entry not in excluding[type]:
                        logger.debug(f"...ok we found another: {chosen_entry.text}")
                        break
            else:
                # create the forbidden entries type array for this type of entry if it doesn't exist
                excluding[type] = list()
            entry = chosen_entry.text  # store the chosen entry
            # add the entry to the array of the entry type in the forbidden entries array
            excluding[type].append(entry)
            # # TODO
            # try:  # if there is a gender attribute to the data
            #     gender = chosen_entry.gender
            # except:
            #     gender = ""
            return (entry, excluding)
        return None
