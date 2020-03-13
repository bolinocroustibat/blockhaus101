import json
import os
from random import randint, randrange, choice
from datetime import datetime, timedelta
from django.db import models
from django.conf import settings

from blockhaus101_app.functions import (
    choose_random_word,
    add_string_to_sentence,
    correct_sentence,
    strtr,
    unique_slugify,
)
from .utils import logger


class Language(models.Model):
    LANGUAGE_CHOICES = (("en", "english"), ("fr", "french"))
    language = models.CharField(
        "language", max_length=2, choices=LANGUAGE_CHOICES, default="fr"
    )


class SiteSettings(models.Model):

    lang = models.ForeignKey(
        Language, related_name="language_sitesettings", on_delete="PROTECT"
    )
    description = models.TextField("header text", max_length=1000, default="")
    period = models.IntegerField("period between two exhibitions, in days", default=7)

    class Meta:
        verbose_name = "General settings"


class Artist(models.Model):

    lang = models.ForeignKey(
        Language, related_name="language_artist", on_delete="PROTECT"
    )
    name = models.CharField("artist name", max_length=80)
    GENDER_CHOICES = (("f", "female"), ("m", "male"))
    gender = models.CharField("artist gender", max_length=6, choices=GENDER_CHOICES)
    discipline = models.CharField("artiste discipline", max_length=80)
    bio = models.TextField("artist biography", max_length=2000)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def generate(self):
        # first name and genre
        firstnames_list = json.load(
            open(os.path.join(settings.JSON_PATH, "FIRSTNAME.json"))
        )
        firstname_list = choice(firstnames_list)
        firstname = firstname_list[0]
        self.gender = firstname_list[1]
        # last name
        lastname_list = json.load(
            open(os.path.join(settings.JSON_PATH, "LASTNAME.json"))
        )
        lastname = choice(lastname_list)[0]
        # full name
        self.name = firstname + " " + lastname
        # discipline
        discipline_list = json.load(
            open(os.path.join(settings.JSON_PATH, "DISCIPLINE.json"))
        )
        self.discipline = choice(discipline_list)[0]
        # bio
        forbidden_words = (
            dict()
        )  # dictionnary which stores words that have been already used in the sentence
        self.bio = self.bio + " " + self.create_bio_sentence(forbidden_words, 4, 7)
        self.bio = self.bio + " " + self.create_bio_sentence(forbidden_words, 8, 12)
        self.bio = self.bio + " " + self.create_bio_sentence(forbidden_words, 13, 22)
        if randint(1, 3) == 2:
            self.bio = (
                self.bio + " " + self.create_bio_sentence(forbidden_words, 22, 29)
            )
        logger.debug(
            "Les mots de la biographie déjà utilisés et à ne pas réutiliser sont : {}".format(
                forbidden_words
            )
        )

    def create_bio_sentence(self, forbidden_words, min_line=None, max_line=None):
        biosentence = ""
        possible_structures_list = json.load(
            open(os.path.join(settings.JSON_PATH, "bio.json"))
        )
        if min_line and max_line:
            nb = randint(min_line - 4, max_line - 4)
        else:
            nb = randrange(0, len(possible_structures_list))
        bio_structure = possible_structures_list[nb]
        index_dict = json.load(open(os.path.join(settings.JSON_PATH, "index.json")))
        pos = 0
        for w in bio_structure:
            if w == "SELF":  # si c'est l'artiste
                biosentence = add_string_to_sentence(biosentence, pos, self.name)
            elif w == "SELFDISCIPLINE":
                biosentence = add_string_to_sentence(biosentence, pos, self.discipline)
            elif w == "EXPO":
                biosentence = add_string_to_sentence(
                    biosentence, pos, self.create_expo_title()
                )
            elif (
                w in index_dict.keys()
            ):  # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
                chosen_word = choose_random_word(
                    word_type=w, forbidden_words=forbidden_words
                )
                biosentence = add_string_to_sentence(biosentence, pos, chosen_word)
            else:  # si l'élément est inconnu, c'est que c'est un mot et pas un code !
                biosentence = add_string_to_sentence(biosentence, pos, w)
            pos += 1
        biosentence = correct_sentence(biosentence)
        if self.gender == "f":  # si l'artiste est du genre féminin
            biosentence = biosentence.replace(" il ", " elle ")
            biosentence = biosentence.replace("qu'il ", "qu'elle ")
            biosentence = biosentence.replace("Il ", " Elle ")
            biosentence = biosentence.replace(" né ", " née ")
            biosentence = biosentence.replace("Né ", "Née ")
            biosentence = biosentence.replace("iplômé ", "iplômée ")
            biosentence = biosentence.replace("marqué ", "marquée ")
            biosentence = biosentence.replace("obsédé ", "obsédée ")
        return biosentence

    def create_expo_title(self):
        title = ""
        possible_structures_list = json.load(
            open(os.path.join(settings.JSON_PATH, "expos.json"))
        )
        expo_structure = choice(possible_structures_list)
        index_dict = json.load(open(os.path.join(settings.JSON_PATH, "index.json")))
        pos = 0
        forbidden_words = (
            dict()
        )  # dictionnary which stores words that have been already used in the sentence
        for w in expo_structure:
            if w == "SELF":  # si c'est l'artiste
                title = add_string_to_sentence(title, pos, self.name)
            elif w == "SELFDISCIPLINE":
                title = add_string_to_sentence(title, pos, self.discipline)
            elif (
                w in index_dict.keys()
            ):  # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
                chosen_word = choose_random_word(
                    word_type=w, forbidden_words=forbidden_words
                )
                title = add_string_to_sentence(title, pos, chosen_word)
            else:  # si l'élément est inconnu, c'est que c'est un mot et pas un code !
                title = add_string_to_sentence(title, pos, w)
            pos += 1
        # title = correct_sentence(title)
        logger.debug(
            "Les mots du titre de l'expo déjà utilisés et à ne pas réutiliser sont : {}".format(
                forbidden_words
            )
        )
        return title


class Exhibition(models.Model):

    lang = models.ForeignKey(
        Language, related_name="language_exhibition", on_delete="PROTECT"
    )
    title = models.CharField("exhibition title", max_length=80)
    artist = models.ForeignKey(
        Artist, related_name="artist_exhibition", on_delete="PROTECT"
    )
    startdate = models.DateTimeField("exhibition start date", blank=True, null=True)
    enddate = models.DateTimeField("exhibition end date", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.startdate or not self.enddate:
            try:
                period = SiteSettings.objects.get().period
            except:
                period = 7
            logger.debug("NOW TRYING TO SAVE NEW EXHIBITION...")
            try:
                self.startdate = Exhibition.objects.latest("enddate").enddate
                self.enddate = self.startdate + timedelta(days=period)
                logger.debug(
                    "AT LEAST ONE EXHIBITION ALREADY PRESENT, EXHIBITION SAVED ACCORDING TO PREVIOUS!"
                )
            except:
                self.startdate = datetime.now()
                self.enddate = datetime.now() + timedelta(days=period)
                logger.debug(
                    "NO EXHIBITIONS ALREADY PRESENT, FIRST EXHIBITION TO SAVE!"
                )
        super(Exhibition, self).save(*args, **kwargs)

    def generate(self):
        self.title = self.artist.create_expo_title()


class ExpoText(models.Model):

    lang = models.ForeignKey(
        Language, related_name="language_expotext", on_delete="PROTECT"
    )
    text = models.TextField("exhibition text", max_length=3000)
    exhibition = models.ForeignKey(
        Exhibition,
        related_name="exhibition_expotext",
        on_delete="PROTECT",
        verbose_name="Exposition",
    )
    slug = models.SlugField(
        default=None, null=True, blank=True, max_length=150, verbose_name="URL"
    )
    ip = models.GenericIPAddressField("creator IP address", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text[:60]

    class Meta:
        verbose_name = "Exhibition text"
        verbose_name_plural = "Exhibitions texts"

    def save(self, *args, **kwargs):
        slug_string = "{}-{}".format(self.exhibition.artist.name, self.exhibition.title)
        unique_slugify(self, slug_string)
        super(ExpoText, self).save(*args, **kwargs)

    def generate(self, ip=None):
        self.ip = ip
        self.text = ""
        forbidden_words = (
            dict()
        )  # dictionnary which stores words that have been already used in the sentence
        if randint(1, 3) == 1:
            self.text = (
                self.text
                + " "
                + self.create_expo_sentence("phrases", forbidden_words, 4, 4)
            )
        self.text = (
            self.text
            + " "
            + self.create_expo_sentence("phrases", forbidden_words, 5, 17)
        )
        if randint(1, 3) == 1:
            self.text = (
                self.text
                + " "
                + self.create_expo_sentence("phrases", forbidden_words, 18, 21)
            )
        self.text = (
            self.text
            + " "
            + self.create_expo_sentence("phrases", forbidden_words, 22, 31)
        )
        self.text = (
            self.text
            + " "
            + self.create_expo_sentence("phrases", forbidden_words, 32, 43)
        )
        self.text = (
            self.text
            + " "
            + self.create_expo_sentence("phrases", forbidden_words, 44, 46)
        )
        if self.exhibition.artist.gender == "f":  # si l'artiste est du genre féminin
            self.text = self.text.replace(" Il ", " Elle ")
        logger.debug(
            "Les mots du texte du médiateur culturel déjà utilisés et à ne pas réutiliser sont : {}".format(
                forbidden_words
            )
        )

    def create_expo_sentence(
        self, guide_file: str(), forbidden_words, min_line=None, max_line=None
    ):
        possible_structures_list = json.load(
            open(os.path.join(settings.JSON_PATH, "{}.json".format(guide_file)))
        )
        # sentences_struc = { int(key):sentences_struc[key] for key in sentences_struc } # convert string keys to integer keys
        if min_line and max_line:
            nb = randint(min_line - 4, max_line - 4)
        else:
            nb = randrange(0, len(possible_structures_list))
        structure = possible_structures_list[nb]
        index_dict = json.load(open(os.path.join(settings.JSON_PATH, "index.json")))
        sentence = ""
        pos = 0
        for w in structure:
            if w == "SELF":  # si c'est l'artiste
                sentence = add_string_to_sentence(
                    sentence, pos, self.exhibition.artist.name
                )
            elif w == "SELFDISPLINE":
                sentence = add_string_to_sentence(
                    sentence, pos, self.exhibition.artist.discipline
                )
            elif w == "SELFEXPO":
                sentence = add_string_to_sentence(sentence, pos, self.exhibition.title)
            elif w == "EXPO":
                sentence = add_string_to_sentence(
                    sentence, pos, self.exhibition.artist.create_expo_title()
                )
            elif (
                w in index_dict.keys()
            ):  # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
                chosen_word = choose_random_word(
                    word_type=w, forbidden_words=forbidden_words
                )
                sentence = add_string_to_sentence(sentence, pos, chosen_word)
            else:  # si l'élément est inconnu, c'est que c'est un mot et pas un code !
                sentence = add_string_to_sentence(sentence, pos, w)
            pos += 1
        sentence = correct_sentence(sentence)
        return sentence

