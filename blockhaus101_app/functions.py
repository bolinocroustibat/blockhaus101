import json
import os
import re
import blockhaus101_app
from random import choice
from django.conf import settings
from django.template.defaultfilters import slugify


########################################
## COMMON FUNCTIONS TO SEVERAL CLASSES #
########################################

def choose_random_word(type: str()):
	words_dict = json.load(open(os.path.join(settings.JSON_PATH, '{}.json'.format(type))))
	chosen_word = choice(words_dict)
	try: #s'il y a une deuxième colonne au tableau, on la met dans un genre
		gender = chosen_word[1]
	except:
		gender = ""
	return chosen_word[0]


def add_string_to_sentence(sentence: str(), pos: int(), string: str()):
	if (pos == 0) or (sentence[-1:] == "-") or (sentence[-1:] == "“") or (sentence[-1:] == '"') or (string[:1] == ",") or (string[:1] == ".") or (string[:1] == "²") or (string[:1] == "”") or (string[:1] == '"'): # pas d'espace avant si c'est le premier mot de la phrase, si le mot précédent se termine par un tiret ou un guillemet ouvrant, ou si le mot suivant est un point ou une virgule ou un carré ou un guillemet fermant
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


"""
Taken from SmileyChris' post @ https://djangosnippets.org/snippets/690/
"""
import re

from django.template.defaultfilters import slugify


def unique_slugify(instance, value, slug_field_name='slug', queryset=None,slug_separator='-'):
	"""
	Calculates a unique slug of ``value`` for an instance.

	``slug_field_name`` should be a string matching the name of the field to
	store the slug in (and the field to check against for uniqueness).

	``queryset`` usually doesn't need to be explicitly provided - it'll default
	to using the ``.all()`` queryset from the model's default manager.
	"""
	slug_field = instance._meta.get_field(slug_field_name)

	slug = getattr(instance, slug_field.attname)
	slug_len = slug_field.max_length

	# Sort out the initial slug. Chop its length down if we need to.
	slug = slugify(value)
	if slug_len:
		slug = slug[:slug_len]
	slug = _slug_strip(slug, slug_separator)
	original_slug = slug

	# Create a queryset, excluding the current instance.
	if not queryset:
		queryset = instance.__class__._default_manager.all()
		if instance.pk:
			queryset = queryset.exclude(pk=instance.pk)

	# Find a unique slug. If one matches, at '-2' to the end and try again
	# (then '-3', etc).
	next = 2
	while not slug or queryset.filter(**{slug_field_name: slug}):
		slug = original_slug
		end = '-%s' % next
		if slug_len and len(slug) + len(end) > slug_len:
			slug = slug[:slug_len-len(end)]
			slug = _slug_strip(slug, slug_separator)
		slug = '%s%s' % (slug, end)
		next += 1

	setattr(instance, slug_field.attname, slug)


def _slug_strip(value, separator=None):
	"""
	Cleans up a slug by removing slug separator characters that occur at the
	beginning or end of a slug.

	If an alternate separator is used, it will also replace any instances of
	the default '-' separator with the new separator.
	"""
	if separator == '-' or not separator:
		re_sep = '-'
	else:
		re_sep = '(?:-|%s)' % re.escape(separator)
		value = re.sub('%s+' % re_sep, separator, value)
	return re.sub(r'^%s+|%s+$' % (re_sep, re_sep), '', value)