from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
import os
import re
import requests
import urllib
import xmltodict
import json
from datetime import datetime
import blockhaus101_app
from .models import *

def index(request):
	try: # try to get an artist for current period
		artist = (Artist.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
		# expo_title = ExpoTitle.objects.filter(artist=artist) # in case we also want a fixes title, do something like that
		print("CURRENT ARTIST : {}".format(artist.name))
	except:
		artist = Artist()
		Artist.generate(artist)
		artist.save()
		print("THERE IS NO CURRENT ARTIST IN THE TIME RANGE, {} HAS BEEN GENERATED AND SAVED".format(artist.name))
	expo_title = ExpoTitle()
	ExpoTitle.generate(expo_title, artist)
	expo_title.save()
	expo_text = ExpoText()
	ExpoText.generate(expo_text, artist)
	expo_text.title = expo_title
	expo_text.save()
	return render(request,'index.html', {'artist_name': artist.name, 'artist_bio': artist.bio, 'expo_title': expo_title.title, 'expo_text': expo_text.text, 'artist_gender': artist.gender})

def exhibition(request, slug):
	try: # get expo + artist from database from expo slug
		expo_text = ExpoText.objects.get(slug=slug)
		expo_title = ExpoTitle.objects.get(title_expotext=expo_text)
		artist = Artist.objects.get(artist_expotitle=expo_title)
		return render(request,'index.html', {'artist_name': artist.name, 'artist_bio': artist.bio, 'expo_title': expo_title.title, 'expo_text': expo_text.text, 'artist_gender': artist.gender})
	except ExpoText.DoesNotExist:
		raise Http404("Cette expo n'existe pas")

def past_exhibitions(request):
	full_exhibs = list()
	artists = Artist.objects.filter(enddate__lte=datetime.now()) # get all artist with enddate before today
	for a in artists:
		items = dict()
		items["startdate"] = a.startdate
		items["enddate"] = a.enddate
		expo_title = ExpoTitle()
		ExpoTitle.generate(expo_title, a)
		expo_text = ExpoText()
		ExpoText.generate(expo_text, a)
		items["name"] = a.name
		items["bio"] = a.bio
		items["title"] = expo_title.title
		items["text"] = expo_text.text
		full_exhibs.append(items)
	return render(request,'past_exhibitions.html', {'full_exhibs': full_exhibs})

def generate(request):
	artist = Artist()
	Artist.generate(artist)
	artist.save()
	return render(request,'generate.html', {'artist_name': artist.name, 'artist_bio': artist.bio, 'artist_startdate': artist.startdate, 'artist_enddate': artist.enddate})

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
