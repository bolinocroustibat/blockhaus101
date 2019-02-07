from django.test import TestCase

import re
import requests
from collections import OrderedDict
import urllib
import xmltodict
import json

import blockhaus101_app
from .models import *
from .utils import logger


class TestGetData(TestCase):

	def test_get_googledocs(self):
		google_sheet_url = "https://docs.google.com/spreadsheets/d/1PrD3UqdqmJM_GpTwfN_JSxQjs6TmsxGxVijUHQ4N58Y/edit#gid=6545"
		path = os.path.join(os.path.dirname(blockhaus101_app.__file__), 'json_data')
		if not os.path.exists(path):
			logger.debug("LE REPERTOIRE DE CAHE N'EXISTE PAS, ON LE CREE")
			os.makedirs(path)
		found_key = re.search('/d/(.+?)/', google_sheet_url)
		if found_key:
			spreadsheet_key = found_key.group(1)
		xml_url = "https://spreadsheets.google.com/feeds/worksheets/{}/public/full".format(spreadsheet_key)
		file = urllib.request.urlopen(xml_url)
		data = file.read()
		file.close()
		datadict = xmltodict.parse(data)
		index_dict = dict((e["title"]['#text'], e["id"].partition("/full/")[2]) for e in list(datadict.items())[0][1]["entry"])  # Build an index dictionnary with the tab title as key, and as the value, the new tab id by separating the url of the google spreasheet tab in 3 parts around "/full/" and takes the third part (after the "full")
		# logger.debug(index_dict) # TEST
		self.assertTrue(len(index_dict) > 1)
		json_data = json.dumps(data)
		self.assertEqual(type(json_data), 'json')
		# logger.info(json_data)


class TestGenerateContent(TestCase):

	artist = Artist()
	exhibition = Exhibition()

	def test_generate_exhibition(self):
		try: # try to get an artist for current period
			self.exhibition = (Exhibition.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
			self.artist = Artist.objects.filter(artist_exhibition=self.exhibition)[0]
		except Exception as e:
			logger.info(e)
			logger.info("THERE IS NO CURRENT EXHIBITION IN THE TIME RANGE")
		self.artist = self.artist.generate()
		logger.info('NEW ARTIST "{}" HAS BEEN GENERATED AND SAVED'.format(self.artist.name))
		self.exhibition.artist = self.artist
		self.exhibition.generate()
		logger.info('NEW EXHIBITION "{}" HAS BEEN GENERATED AND SAVED'.format(self.exhibition.title))

	def test_generate_tweet(self):
		try:
			tweet = ""
			possible_structures_list = json.load(open(os.path.join(settings.JSON_PATH, 'tweets.json')))
			nb = randrange(0,len(possible_structures_list))
			tweet_structure = possible_structures_list[nb]
			index_dict = json.load(open(os.path.join(settings.JSON_PATH, 'index.json')))
			pos = 0
			for w in tweet_structure:
				if w == "SELF": # si c'est l'artiste
					tweet = add_string_to_sentence(tweet, pos, self.artist.name)
				elif w == "SELFDISCIPLINE":
					tweet = add_string_to_sentence(tweet, pos, self.artist.discipline)
				elif w == "EXPO":
					tweet = add_string_to_sentence(tweet, pos, self.exhibition.title)
				elif w == "EXPOSTARTDATE":
					expo_startdate_string = '{:%d %B}'.format(self.exhibition.startdate)
					if expo_startdate_string[0] == "0":
						expo_startdate_string = expo_startdate_string[1:]
					tweet = add_string_to_sentence(tweet, pos, expo_startdate_string)
				elif w == "EXPOENDDATE":
					expo_enddate_string = '{:%d %B}'.format(self.exhibition.enddate)
					if expo_enddate_string[0] == "0":
						expo_enddate_string = expo_enddate_string[1:]
					tweet = add_string_to_sentence(tweet, pos, expo_enddate_string)
				elif w in index_dict.keys(): # s'il s'agit d'un code de mot parmi ceux dont le nombre et le genre doivent être déterminés
					tweet = add_string_to_sentence(tweet, pos, choose_random_word(w))
				else: # si l'élément est inconnu, c'est que c'est un mot et pas un code !
					tweet = add_string_to_sentence(tweet, pos, w)
				pos += 1
			tweet = correct_sentence(tweet)
		except Exception as e:
			logger.error("ERROR WHILE CREATING THE TWEET")
		logger.info("TWEET GÉNÉRÉ : {}".format(tweet))
