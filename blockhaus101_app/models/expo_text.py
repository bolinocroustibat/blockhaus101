import json
import os
from random import randint, randrange
from django.db import models
from django.conf import settings

from blockhaus101_app.functions import (
	choose_random_word,
	add_string_to_sentence,
	correct_sentence,
	unique_slugify,
)
from blockhaus101_app.models.language import Language
from blockhaus101_app.models.exhibition import Exhibition
from blockhaus101_app.models.sitesetting import SiteSetting
from blockhaus101_app.utils import logger


class ExpoText(models.Model):

	language = models.ForeignKey(
		Language, related_name="expotexts", on_delete=models.PROTECT
	)
	text = models.TextField("exhibition text", max_length=3000)
	exhibition = models.ForeignKey(
		Exhibition,
		related_name="expotexts",
		on_delete=models.PROTECT,
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
		unique_slugify(self, slug_string) # if this slug exists for others, add a number at the end of the slug attribute of the instance 
		super(ExpoText, self).save(*args, **kwargs)

	def generate(self, ip:str=None) -> None:
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
	) -> str:
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
