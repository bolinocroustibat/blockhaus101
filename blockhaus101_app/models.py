from django.db import models
from solo.models import SingletonModel
import json
import os
from random import randint, randrange, choice
from django.conf import settings
from datetime import datetime, timedelta
from blockhaus101_app.functions import choose_random_word, add_string_to_sentence, correct_sentence, strtr, unique_slugify


class SiteSettings(SingletonModel):
	manifesto = models.TextField("Texte du manifeste", max_length=3000, default="")
	period = models.IntegerField("Période entre deux expositions, en jours", default=7)
	class Meta:
		verbose_name = "Réglages généraux de Blockhaus101"

class Artist(models.Model):
	name = models.CharField("Nom de l'artiste", max_length=80)
	GENDER_CHOICES =(
		('f', 'female'),
		('m', 'male')
	)
	gender = models.CharField("Genre de l'artiste", max_length=6, choices=GENDER_CHOICES)
	discipline = models.CharField("Discipline de l'artiste", max_length=80)
	bio = models.TextField("Biographie de l'artiste", max_length=2000)
	created = models.DateTimeField(auto_now=True)
	def __str__(self):
		return (self.name)
	class Meta:
		verbose_name = "Artiste"
		verbose_name_plural = "Artistes"
	def generate(self):
		# first name and genre
		firstnames_list = json.load(open(os.path.join(settings.JSON_PATH, 'FIRSTNAME.json')))
		firstname_list = choice(firstnames_list)
		firstname = firstname_list[0]
		self.gender = firstname_list[1]
		# last name
		lastname_list = json.load(open(os.path.join(settings.JSON_PATH, 'LASTNAME.json')))
		lastname = choice(lastname_list)[0]
		# full name
		self.name = firstname + ' ' + lastname
		# discipline
		discipline_dict = json.load(open(os.path.join(settings.JSON_PATH, 'DISCIPLINE.json')))
		self.discipline = choice(discipline_dict)[0]
		# bio
		self.bio = self.bio + ' ' + self.create_bio_sentence(4, 6)
		self.bio = self.bio + ' ' + self.create_bio_sentence(7, 11)
		if randint(1, 3) == 3:
			self.bio = self.bio + ' ' + self.create_bio_sentence(12, 16)
		self.bio = self.bio + ' ' + self.create_bio_sentence(17, 20)

	def create_bio_sentence(self, min_line = None, max_line = None):
		biosentence = ""
		possible_structures_list = json.load(open(os.path.join(settings.JSON_PATH, 'bio.json')))
		if min_line and max_line:
			nb = randint(min_line-4, max_line-4)
		else:
			nb = randrange(0,len(possible_structures_list))
		bio_structure = possible_structures_list[nb]
		index_dict = json.load(open(os.path.join(settings.JSON_PATH, 'index.json')))
		pos = 0
		for v in bio_structure:
			if v == "SELF": # si c'est l'artiste
				biosentence = add_string_to_sentence(biosentence, pos, self.name)
			elif v == "SELFDISCIPLINE":
				biosentence = add_string_to_sentence(biosentence, pos, self.discipline)
			elif v == "EXPO":
				biosentence = add_string_to_sentence(biosentence, pos, self.create_expo_title())
			elif v in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
				biosentence = add_string_to_sentence(biosentence, pos, choose_random_word(v))
			else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
				biosentence = add_string_to_sentence(biosentence, pos, v)
			pos += 1
		biosentence = correct_sentence(biosentence)
		if self.gender == "f": # si l'artiste est du genre féminin
			biosentence = biosentence.replace(" il ", " elle ")
			biosentence = biosentence.replace(" né ", " née ")
			biosentence = biosentence.replace("Né ", "Née ")
		return biosentence

	def create_expo_title(self):
		title = ""
		possible_structures_list = json.load(open(os.path.join(settings.JSON_PATH, 'expos.json')))
		expo_structure = choice(possible_structures_list)
		index_dict = json.load(open(os.path.join(settings.JSON_PATH, 'index.json')))
		pos = 0
		for w in expo_structure:
			if w == "SELF": # si c'est l'artiste
				title = add_string_to_sentence(title, pos, self.name)
			elif w == "SELFDISCIPLINE":
				title = add_string_to_sentence(title, pos, self.discipline)
			elif w in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
				title = add_string_to_sentence(title, pos, choose_random_word(w))
			else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
				title = add_string_to_sentence(title, pos, w)
			pos += 1
		#title = correct_sentence(title)
		return title


class Exhibition(models.Model):
	title = models.CharField("Titre de l'exposition", max_length=80)
	artist = models.ForeignKey(Artist, related_name="artist_exhibition", on_delete="PROTECT")
	startdate = models.DateTimeField("Date de début d'exposition", blank=True, null=True)
	enddate = models.DateTimeField("Date de fin d'exposition", blank=True, null=True)
	created = models.DateTimeField(auto_now=True)
	def __str__(self):
		return (self.title)
	class Meta:
		verbose_name = "Exposition"
		verbose_name_plural = "Expositions"
	def save(self, *args, **kwargs):
		try:
			period = SiteSettings.objects.get().period
		except:
			period = 7
		print("## NOW TRYING TO SAVE NEW EXHIBITION...")
		try:
			self.startdate = Exhibition.objects.latest('enddate').enddate
			self.enddate = self.startdate + timedelta(days=period)
			print("## AT LEAST ONE EXHIBITION ALREADY PRESENT, EXHIBITION SAVED ACCORDING TO PREVIOUS!")
		except:
			self.startdate = datetime.now()
			self.enddate = datetime.now() + timedelta(days=period)
			print("## NO EXHIBITIONS ALREADY PRESENT, FIRST EXHIBITION TO SAVE!")
		super(Exhibition, self).save(*args, **kwargs)
	def generate(self, artist: Artist()):
		self.artist = artist
		self.title = artist.create_expo_title() 


class ExpoText(models.Model):
	text = models.TextField("Texte de l'exposition", max_length=3000)
	exhibition = models.ForeignKey(Exhibition, related_name="exhibition_expotext", on_delete="PROTECT", verbose_name="Exposition")
	slug = models.SlugField(default=None, null=True, blank=True,max_length=150, verbose_name="URL")
	ip = models.GenericIPAddressField("Adresse IP du créateur", blank=True, null=True)
	created = models.DateTimeField(auto_now=True)
	def __str__(self):
		return (self.text[:60])
	class Meta:
		verbose_name = "Texte d'expositions"
		verbose_name_plural = "Textes d'expositions"
	def save(self, *args, **kwargs):
		slug_string = "{}-{}".format(self.exhibition.artist.name, self.exhibition.title)
		unique_slugify(self, slug_string)
		super(ExpoText, self).save(*args, **kwargs)
	def generate(self, artist: Artist(), ip=None):
		self.ip = ip
		self.text = ""
		if randint(1, 2) == 2:
			self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 4, 4)
		self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 5, 9)
		if randint(1, 3) == 3:
			self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 10, 13)
		self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 14, 23)
		self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 24, 36)
	def create_expo_sentence(self, guide_file: str(), artist: Artist(), min_line = None, max_line = None):
		possible_structures_list = json.load(open(os.path.join(settings.JSON_PATH, '{}.json'.format(guide_file))))
		#sentences_struc = { int(key):sentences_struc[key] for key in sentences_struc } # convert string keys to integer keys
		if min_line and max_line:
			nb = randint(min_line-4, max_line-4)
		else:
			nb = randrange(0,len(possible_structures_list))
		structure = possible_structures_list[nb]
		index_dict = json.load(open(os.path.join(settings.JSON_PATH, 'index.json')))
		sentence = ""
		pos = 0
		for w in structure:
			if w == "SELF": # si c'est l'artiste
				sentence = add_string_to_sentence(sentence, pos, artist.name)
			elif w == "SELFDISPLINE":
				sentence = add_string_to_sentence(sentence, pos, artist.discipline)
			elif w == "EXPO":
				sentence = add_string_to_sentence(sentence, pos, artist.create_expo_title())
			elif w in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
				sentence = add_string_to_sentence(sentence, pos, choose_random_word(w))
			else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
				sentence = add_string_to_sentence(sentence, pos, w)
			pos += 1
		sentence = correct_sentence(sentence)
		return sentence
