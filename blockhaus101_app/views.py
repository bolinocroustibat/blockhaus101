from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
import os
import re
import requests
import urllib
import xmltodict
import json
import blockhaus101_app
from blockhaus101_app.create import Artist, Expo

import random
path = os.path.join(os.path.dirname(blockhaus101_app.__file__), 'json_data')

def index(request):
	# verify if id of expo by GET
	# if yes:
		# get expo + artist from database
		# send to the template for display
	# if no:
		# checks if there is an artist for this period
		# if yes:
			# get last/current artist from database
			# generate expo with this artist
			# record expo in the database
			# send to the template for display
		# if no:
			# generate new artist
			# records it in the database
			# send to the template for display

	artist = Artist()
	expo_title = Expo(artist).title
	expo_text = Expo(artist).text
	html = render_to_string('index.html', {'artist_name': artist.name, 'artist_bio': artist.bio, 'expo_title': expo_title, 'expo_text': expo_text, 'artist_gender': artist.gender})
	return HttpResponse(html)


def build_json(request):
	url = "https://docs.google.com/spreadsheets/d/1PrD3UqdqmJM_GpTwfN_JSxQjs6TmsxGxVijUHQ4N58Y/edit#gid=6545"
	path = os.path.join(os.path.dirname(blockhaus101_app.__file__), 'json_data')
	found_key = re.search('/d/(.+?)/', url)
	if found_key:
		spreadsheet_key = found_key.group(1)
	xml_url = "https://spreadsheets.google.com/feeds/worksheets/{}/public/full".format(spreadsheet_key)
	file = urllib.request.urlopen(xml_url)
	data = file.read()
	file.close()
	datadict = xmltodict.parse(data)
	index_dict = dict((e["title"]['#text'], e["id"].partition("/full/")[2]) for e in list(datadict.items())[0][1]["entry"])  # Build an index dictionnary with KEY as the tab title, and the VALUE as the new tab id by separating the url of the google spreasheet tab in 3 parts around "/full/" and takes the third part (after the "full")
	print(index_dict) # TEST
	try:
		with open(os.path.join(path, 'index2.json'), 'w') as outfile:
			outfile.write(json.dumps(index_dict))
		print('Index cache file "index2.json" was successfully created!')
	except:
		print('ERROR WHILE TRYING TO CREATE INDEX FILE')
	for key, value in index_dict.items():
		try:
			json_url = "https://spreadsheets.google.com/feeds/list/{}/{}/public/values?alt=json".format(spreadsheet_key, value)
			print(json_url) # TEST
			json_data = requests.get(json_url).json()
			trimmed_json_data = dict()
			for i, e in enumerate(json_data['feed']['entry'][2:]): # loops through the interesting rows and removes the 3 first rows
				trimmed_json_data[i] = {k: v["$t"] for k, v in e.items() if k.startswith('gsx')}
			with open(os.path.join(path, '{}.json'.format(key)), 'w') as outfile:
				outfile.write(json.dumps(trimmed_json_data))
			print('JSON cache file "{}" was successfully created!'.format(key))
		except:
			print('ERROR WHILE TRYING TO CACHE "{}"'.format(key))
	return HttpResponse('{}'.format("Les fichiers de cache ont été créés !"))


def past_exhibitions(request):
	pass

def test(request):
	artist = Artist()
	return HttpResponse(artist.name)