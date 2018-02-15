import json
import os
import blockhaus101_app
import random
from random import randint

path = os.path.join(os.path.dirname(blockhaus101_app.__file__), 'json_data')


########################################
## COMMON FUNCTIONS TO SEVERAL CLASSES #
########################################

def choose_random_word(type: str()):
	words_dict = json.load(open(os.path.join(path, '{}.json'.format(type))))
	nb = random.choice(list(words_dict.keys()))
	word = list(words_dict[nb].values())[0]
	try: #s'il y a une deuxième colonne au tableau, on la met dans un genre
		gender = list(words_dict[nb].values())[1]
	except:
		gender = ""
	return word


def add_string_to_sentence(sentence: str(), pos: int(), string: str()):
	if (pos == 0) or (sentence[-1:] == ("-" or "“")) or (string[:1] == ("." or "," or "²" or "”")): # pas d'espace avant si c'est le premier mot de la phrase, si le mot précédent se termine par un guillemet ouvrant, ou si le mot suivant est un point ou une virgule ou un carré ou un guillemet fermant
		sentence = sentence + string
	else:
		sentence = sentence + ' ' + string
	return sentence

def correct_sentence(sentence: str()):
	correction_dict = { # we could also use "replace(old, new)": https://www.tutorialspoint.com/python/string_replace.htm
	"( ": "(",
	" )": ")",
	" à le ": " au ",
	" à les ": " aux ",
	" de a": " d’a",
	" de e": " d’e",
	" de ê": " d’ê",
	" de ê": " d’ê",
	" de é": " d’é",
	" de è": " d’è",
	" de h": " d’h",
	" de i": " d’i",
	" de u": " d’u",
	" de A": " d’A",
	" de E": " d’E",
	" de I": " d’I",
	" de de ": " de ",
	" de des ": " des ",
	" de le ": " du ",
	" de les ": " des ",
	" en la ": " en ",
	" en le ": " en ",
	" en les ": " en ",
	" la A": " l’A",
	" la E": " l’E",
	" la É": " l’É",
	" la U": " l’U",
	" la I": " l’I",
	" la O": " l’O",
	" le A": " l’A",
	" le E": " l’E",
	" le É": " l’É",
	" le U": " l’U",
	" le I": " l’I",
	" le O": " l’O",
	" le la ": " la ",
	" le le ": " le ",
	" le les ": " les ",
	" un l’": " un ",
	" un la ": " une ",
	" un le ": " un ",
	" un les ": " des ",
	" son la ": " sa ",
	" son le ": " son ",
	" son l’": " son ",
	" son les ": " ses ",
	" que a": " qu’a",
	" que e": " qu’e",
	" que i": " qu’i",
	" que u": " qu’u",
	" que A": " qu’A",
	" que E": " qu’E",
	" que I": " qu’I",
	" que U": " qu’U",
	}
	sentence = strtr(sentence, correction_dict)
	if sentence[:1] == ('“' or '"'): # if the first char is a double quote
		sentence_list = list(sentence)
		sentence_list[1] = sentence[1].upper() # uppercase on the second char
		sentence = "".join(sentence_list)
	else:
		sentence = sentence[0].upper() + sentence[1:] # capitalize first letter
	return sentence


def strtr(string, correction_dict: dict()):
	buffer = []
	i, n = 0, len(string)
	while i < n:
		match = False
		for s, r in correction_dict.items():
			if string[i:len(s)+i] == s:
				buffer.append(r)
				i = i + len(s)
				match = True
				break
		if not match:
			buffer.append(string[i])
			i = i + 1
	return ''.join(buffer)



class Artist:

	name = str("")
	gender = str("")
	discipline = str("")
	bio = str("")

	def __init__(self):
		# first name and genre
		firstnames_dict = json.load(open(os.path.join(path, 'FIRSTNAME.json')))
		firstname_nb = random.choice(list(firstnames_dict.keys()))
		firstname = list(firstnames_dict[firstname_nb].values())[0]
		self.gender = list(firstnames_dict[firstname_nb].values())[1]
		# last name
		lastname_dict = json.load(open(os.path.join(path, 'LASTNAME.json')))
		lastname_nb = random.choice(list(lastname_dict.keys()))
		lastname = list(lastname_dict[lastname_nb].values())[0]
		# full name
		self.name = firstname + ' ' + lastname
		# discipline
		discipline_dict = json.load(open(os.path.join(path, 'DISCIPLINE.json')))
		discipline_nb = random.choice(list(discipline_dict.keys()))
		self.discipline = list(discipline_dict[discipline_nb].values())[0]
		# bio
		self.bio = self.bio + ' ' + self.create_bio_sentence(4, 6)
		self.bio = self.bio + ' ' + self.create_bio_sentence(7, 11)
		if randint(1, 3) == 3:
			self.bio = self.bio + ' ' + self.create_bio_sentence(12, 16)
		self.bio = self.bio + ' ' + self.create_bio_sentence(17, 20)

	def create_bio_sentence(self, min_line = None, max_line = None):
		biosentence = ""
		bios_struc = json.load(open(os.path.join(path, 'bio.json')))
		if min_line and max_line:
			nb = randint(min_line-4, max_line-4)
		else:
			nb = int(random.choice(list(bios_struc.keys())))
		self.bio_structure = bios_struc[str(nb)]
		index_dict = json.load(open(os.path.join(path, 'index2.json')))
		pos = 0
		for k,v in self.bio_structure.items():
			if v == "SELF": # si c'est l'artiste
				biosentence = add_string_to_sentence(biosentence, pos, self.name)
			elif v == "SELFDISCIPLINE":
				biosentence = add_string_to_sentence(biosentence, pos, self.discipline)
			elif v == "EXPO":
				biosentence = biosentence + ' ' + self.create_expo_title()
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
		expo_title = ""
		expos_struc = json.load(open(os.path.join(path, 'expos.json')))
		nb = int(random.choice(list(expos_struc.keys())))
		self.expo_structure = expos_struc[str(nb)]
		index_dict = json.load(open(os.path.join(path, 'index2.json')))
		pos = 0
		for k,v in self.expo_structure.items():
			if v == "SELF": # si c'est l'artiste
				expo_title = add_string_to_sentence(expo_title, pos, self.name)
			elif v == "SELFDISCIPLINE":
				expo_title = add_string_to_sentence(expo_title, pos, self.discipline)
			elif v in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
				expo_title = add_string_to_sentence(expo_title, pos, choose_random_word(v))
			else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
				expo_title = add_string_to_sentence(expo_title, pos, v)
			pos += 1
		return expo_title



class Expo:

	title = str("")
	text = str("")

	def __init__(self, artist: Artist()):
		# expo title
		self.title = artist.create_expo_title() 
		# expo text
		self.text = ""
		if randint(1, 2) == 2:
			self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 4, 4)
		self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 5, 9)
		if randint(1, 3) == 3:
			self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 10, 13)
		self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 14, 23)
		self.text = self.text + ' ' + self.create_expo_sentence("phrases", artist, 24, 36)

	def create_expo_sentence(self, guide_file: str(), artist: Artist(), min_line = None, max_line = None):
		sentences_struc = json.load(open(os.path.join(path, '{}.json'.format(guide_file))))
		sentences_struc = { int(key):sentences_struc[key] for key in sentences_struc } # convert string keys to integer keys
		if min_line and max_line:
			self.nb = randint(min_line-4, max_line-4)
		else:
			self.nb = int(random.choice(list(sentences_struc.keys())))
		structure = sentences_struc[self.nb]
		index_dict = json.load(open(os.path.join(path, 'index2.json')))
		sentence = ""
		pos = 0
		for k,v in structure.items():
			if v == "SELF": # si c'est l'artiste
				sentence = add_string_to_sentence(sentence, pos, artist.name)
			elif v == "SELFDISPLINE":
				sentence = add_string_to_sentence(sentence, pos, artist.discipline)
			elif v == "EXPO":
				sentence = add_string_to_sentence(sentence, pos, artist.create_expo_title())
			elif v in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
				sentence = add_string_to_sentence(sentence, pos, choose_random_word(v))
			else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
				sentence = add_string_to_sentence(sentence, pos, v)
			pos += 1
		sentence = correct_sentence(sentence)
		return sentence



