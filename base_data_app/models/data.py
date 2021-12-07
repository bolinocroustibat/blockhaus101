from random import choice
from typing import Optional, Tuple, Union

from django.db import models

from blockhaus101.settings import logger
from base_data_app.models.data_type import DataType


class Data(models.Model):

    type = models.ForeignKey(DataType, related_name="data", on_delete=models.CASCADE)
    text = models.TextField("data", max_length=3000)
    gender = models.CharField("gender / plural", max_length=8, null=True, blank=True)
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
    def choose_random(
        cls, word_type: str, used_words: Optional[dict] = None
    ) -> Union[Tuple[str, dict], None]:
        """
        Choose a random word from the database, according to the type, and to the words already being used before.
        """
        words = cls.objects.filter(type__name=word_type)
        if words:
            chosen_data = choice(words)
            if used_words.get(word_type):
                while chosen_data.text in used_words[word_type]:
                    logger.debug(
                        f"Word '{chosen_data.text}' of type '{word_type}' has been used already, let's choose another"
                    )
                    chosen_data = choice(words)
                    if chosen_data not in used_words[word_type]:
                        logger.debug(f"...ok we found another: {chosen_data.text}")
                        break
            else:
                # create the forbidden words type array for this type of word if it doesn't exist
                used_words[word_type] = list()
            word = chosen_data.text  # store the chosen word
            # add the word to the array of the word type in the forbidden words array
            used_words[word_type].append(word)
            # # TODO
            # try:  # if there is a gender attribute to the data
            #     gender = chosen_data.gender
            # except:
            #     gender = ""
            return (word, used_words)
        return None
