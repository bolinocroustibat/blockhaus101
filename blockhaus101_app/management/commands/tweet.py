import tweepy
from django.core.management.base import BaseCommand
from django.apps import apps

from blockhaus101_app.functions import (
	choose_random_word,
	add_string_to_sentence,
	correct_sentence,
)
from blockhaus101_app.models import *


class Command(BaseCommand):

	help = "Generate new tweet"

	def add_arguments(self, parser):
		parser.add_argument("--tweet1", dest="tweet1", default=False, help=u"Tweet 1")
		parser.add_argument("--tweet2", dest="tweet2", default=False, help=u"Tweet 2")

	def handle(self, *args, **options):
		try:
			# try to get an artist for current period
			exhibition = (
				Exhibition.objects.filter(startdate__lte=datetime.now()).filter(
					enddate__gte=datetime.now()
				)
			)[0]
			artist = Artist.objects.filter(artist_exhibition=exhibition)[0]
			tweet = ""
			forbidden_words = (
				dict()
			)  # dictionnary which stores words that have been already used in the tweet
			if options["tweet1"]:
				logger.info("Generate tweet 1")
				possible_structures_list = json.load(
					open(os.path.join(settings.JSON_PATH, "tweets1.json"))
				)
			else:
				logger.info("Generate tweet 2")
				possible_structures_list = json.load(
					open(os.path.join(settings.JSON_PATH, "tweets2.json"))
				)
			nb = randrange(0, len(possible_structures_list))
			tweet_structure = possible_structures_list[nb]
			index_dict = json.load(open(os.path.join(settings.JSON_PATH, "index.json")))
			pos = 0
			for w in tweet_structure:
				if w == "SELF":  # si c'est l'artiste
					tweet = add_string_to_sentence(tweet, pos, artist.name)
				elif w == "SELFDISCIPLINE":
					tweet = add_string_to_sentence(tweet, pos, artist.discipline)
				elif w == "EXPO":
					tweet = add_string_to_sentence(tweet, pos, exhibition.title)
				elif w == "EXPOSTARTDATE":
					expo_startdate_string = "{:%d %B}".format(exhibition.startdate)
					if expo_startdate_string[0] == "0":
						expo_startdate_string = expo_startdate_string[1:]
					tweet = add_string_to_sentence(tweet, pos, expo_startdate_string)
				elif w == "EXPOENDDATE":
					expo_enddate_string = "{:%d %B}".format(exhibition.enddate)
					if expo_enddate_string[0] == "0":
						expo_enddate_string = expo_enddate_string[1:]
					tweet = add_string_to_sentence(tweet, pos, expo_enddate_string)
				elif (
					w in index_dict.keys()
				):  # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
					chosen_word = choose_random_word(
						word_type=w, forbidden_words=forbidden_words
					)
					tweet = add_string_to_sentence(tweet, pos, chosen_word)
				else:  # si l'élément est inconnu, c'est que c'est un mot et pas un code !
					tweet = add_string_to_sentence(tweet, pos, w)
				pos += 1
			tweet = correct_sentence(tweet)
			logger.debug('Tweet "{}" created'.format(tweet))
			try:
				auth = tweepy.OAuthHandler(
					settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET
				)
				auth.set_access_token(
					settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET
				)
				api = tweepy.API(auth)
				# If the authentication was successful, you should see the name of the account print out
				twitter_account_name = api.me().name
				try:
					# If the application settings are set for "Read and Write" then this line should tweet out the message to your account's timeline. The "Read and Write" setting is on https://dev.twitter.com/apps
					api.update_status(status=tweet)
					logger.info(
						'sent to Twitter account "{}"'.format(twitter_account_name)
					)
				except:
					logger.error(
						'Error while trying to send tweet to "{}" account'.format(
							twitter_account_name
						)
					)
			except Exception as e:
				logger.info("Error while connecting to Twitter account")
				logger.error(e)
		except Exception as e:
			logger.error("Error while creating the tweet:")
			logger.error(e)
