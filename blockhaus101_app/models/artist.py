import json
import os
from random import randint, randrange, choice
from django.db import models
from django.conf import settings

from blockhaus101_app.functions import (
	choose_random_word,
	add_string_to_sentence,
	correct_sentence,
)
from blockhaus101_app.models.language import Language
from blockhaus101_app.utils import logger


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

	def create_bio_sentence(
		self, forbidden_words: dict, min_line: int = None, max_line: int = None
	) -> str:
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

	def create_expo_title(self) -> str:
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
