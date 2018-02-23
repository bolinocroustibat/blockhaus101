from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from blockhaus101_app.functions import choose_random_word, add_string_to_sentence, correct_sentence, strtr, unique_slugify
from blockhaus101_app.models import *

class Command(BaseCommand):
	help = 'Generate new tweet'

	def handle(self, *args, **options):
		try: # try to get an artist for current period
			exhibition = (Exhibition.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
			artist = Artist.objects.filter(artist_exhibition=exhibition)[0]
			tweet = ""
			possible_structures_list = json.load(open(os.path.join(settings.JSON_PATH, 'tweets.json')))
			if min_line and max_line:
				nb = randint(min_line-4, max_line-4)
			else:
				nb = randrange(0,len(possible_structures_list))
			tweet_structure = possible_structures_list[nb]
			index_dict = json.load(open(os.path.join(settings.JSON_PATH, 'index.json')))
			pos = 0
			for w in tweet_structure:
				if w == "SELF": # si c'est l'artiste
					tweet = add_string_to_sentence(tweet, pos, artist.name)
				elif w == "SELFDISCIPLINE":
					tweet = add_string_to_sentence(tweet, pos, artist.discipline)
				elif w == "EXPO":
					tweet = add_string_to_sentence(tweet, pos, exhibition.title)
				elif w in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
					tweet = add_string_to_sentence(tweet, pos, choose_random_word(w))
				else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
					tweet = add_string_to_sentence(tweet, pos, w)
				pos += 1
			tweet = correct_sentence(tweet)
			if artist.gender == "f": # si l'artiste est du genre féminin
				tweet = tweet.replace(" il ", " elle ")
				tweet = tweet.replace(" né ", " née ")
				tweet = tweet.replace("Né ", "Née ")
			print(tweet)
			#return tweet
		except:
			print("ERROR, PROBABLY WHILE TRYING TO GET THE PERIOD ARTIST")
