from datetime import datetime
import os
import json
from random import randrange

from django.test import TestCase

from blockhaus101_app.models import *
from blockhaus101_app.utils import logger
from blockhaus101_app.functions import (
    add_string_to_sentence,
    choose_random_word,
    correct_sentence,
)
from blockhaus101 import settings


class TestGenerateContent(TestCase):

    artist = Artist()
    exhibition = Exhibition()

    def test_generate_exhibition(self):
        try:  # try to get an artist for current period
            self.exhibition = (
                Exhibition.objects.filter(startdate__lte=datetime.now()).filter(
                    enddate__gte=datetime.now()
                )
            )[0]
            self.artist = Artist.objects.filter(artist_exhibition=self.exhibition)[0]
        except Exception as e:
            logger.info(e)
            logger.info("THERE IS NO CURRENT EXHIBITION IN THE TIME RANGE")
        self.artist = self.artist.generate()
        logger.info(
            'NEW ARTIST "{}" HAS BEEN GENERATED AND SAVED'.format(self.artist.name)
        )
        self.exhibition.artist = self.artist
        self.exhibition.generate()
        logger.info(
            'NEW EXHIBITION "{}" HAS BEEN GENERATED AND SAVED'.format(
                self.exhibition.title
            )
        )

    def test_generate_tweet(self):
        try:
            tweet = ""
            possible_structures_list = json.load(
                open(os.path.join(settings.JSON_PATH, "tweets.json"))
            )
            nb = randrange(0, len(possible_structures_list))
            tweet_structure = possible_structures_list[nb]
            index_dict = json.load(open(os.path.join(settings.JSON_PATH, "index.json")))
            pos = 0
            for w in tweet_structure:
                if w == "SELF":  # si c'est l'artiste
                    tweet = add_string_to_sentence(tweet, pos, self.artist.name)
                elif w == "SELFDISCIPLINE":
                    tweet = add_string_to_sentence(tweet, pos, self.artist.discipline)
                elif w == "EXPO":
                    tweet = add_string_to_sentence(tweet, pos, self.exhibition.title)
                elif w == "EXPOSTARTDATE":
                    expo_startdate_string = "{:%d %B}".format(self.exhibition.startdate)
                    if expo_startdate_string[0] == "0":
                        expo_startdate_string = expo_startdate_string[1:]
                    tweet = add_string_to_sentence(tweet, pos, expo_startdate_string)
                elif w == "EXPOENDDATE":
                    expo_enddate_string = "{:%d %B}".format(self.exhibition.enddate)
                    if expo_enddate_string[0] == "0":
                        expo_enddate_string = expo_enddate_string[1:]
                    tweet = add_string_to_sentence(tweet, pos, expo_enddate_string)
                elif (
                    w in index_dict.keys()
                ):  # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
                    tweet = add_string_to_sentence(tweet, pos, choose_random_word(w))
                else:  # si l'élément est inconnu, c'est que c'est un mot et pas un code !
                    tweet = add_string_to_sentence(tweet, pos, w)
                pos += 1
            tweet = correct_sentence(tweet)
        except Exception as e:
            logger.error("ERROR WHILE CREATING THE TWEET")
        logger.info("TWEET GÉNÉRÉ : {}".format(tweet))
