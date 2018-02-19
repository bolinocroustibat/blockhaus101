from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
import os
import re
import requests
import urllib
import xmltodict
import json
from datetime import datetime, timedelta
import blockhaus101_app
from .models import *

def index(request):
	try: # try to get an artist for current period
		# artist = (Artist.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
		# expo_title = ExpoTitle.objects.filter(artist=artist) # in case we also want a fixes title, do something like that
		exhibition = (Exhibition.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
		artist = Artist.objects.filter(artist_exhibition=exhibition)[0]
		print('## CURRENT EXHIBITION DISPLAYED : {} "{}"'.format(artist.name, exhibition.title))
	except:
		print("## THERE IS NO CURRENT EXHIBITION IN THE TIME RANGE")
		artist = Artist()
		Artist.generate(artist)
		artist.save()
		exhibition = Exhibition()
		Exhibition.generate(exhibition, artist)
		exhibition.save()
		print('## NEW ARTIST "{}" HAS BEEN GENERATED AND SAVED'.format(artist.name))
		print('## NEW EXHIBITION "{}" HAS BEEN GENERATED AND SAVED'.format(exhibition.title))
	expo_text = ExpoText()
	try: # store IP adress
		ip = request.META.get('REMOTE_ADDR')
		ExpoText.generate(expo_text, artist, ip)
		print("## IP {}".format(ip))
	except:
		ExpoText.generate(expo_text, artist)
		print("## COULDN'T RETRIEVE IP")
	expo_startdate = exhibition.startdate.date()
	expo_enddate = exhibition.enddate.date()
	expo_text.exhibition = exhibition
	expo_text.save()
	return render(request,'index.html', {'expo_startdate': expo_startdate, 'expo_enddate': expo_enddate, 'artist_name': artist.name, 'artist_bio': artist.bio, 'expo_title': exhibition.title, 'expo_text': expo_text.text, 'artist_gender': artist.gender})

def exhibition(request, slug):
	try: # get expo + artist from database from expo slug
		expo_text = ExpoText.objects.get(slug=slug)
		exhibition = Exhibition.objects.get(exhibition_expotext=expo_text)
		artist = Artist.objects.get(artist_exhibition=exhibition)
		return render(request,'index.html', {'artist_name': artist.name, 'artist_bio': artist.bio, 'expo_title': exhibition.title, 'expo_text': expo_text.text, 'artist_gender': artist.gender})
	except ExpoText.DoesNotExist:
		raise Http404("Cette expo n'existe pas")

def past_exhibitions(request):
	full_exhibs = list()
	exhibitions = Exhibition.objects.filter(enddate__lte=datetime.now()).order_by('-enddate') # get all artist with enddate before today
#	artists = Artist.objects.filter(enddate__lte=datetime.now()) # get all artist with enddate before today
	for e in exhibitions:
		exhibition = dict()
		exhibition["startdate"] = e.startdate.date()
		try: # try to get the startdate of most recent exhibition (previous on the loop
			if e.enddate.date() == previous_expo_startdate: # if this startdate is the same day as the enddate
				exhibition["enddate"] = e.enddate.date() - timedelta(days=1) # remove one day to the enddate
			else:
				exhibition["enddate"] = e.enddate.date()
		except:
			exhibition["enddate"] = e.enddate.date()
		exhibition["title"] = e.title
		exhibition["name"] = e.artist.name
		exhibition["bio"] = e.artist.bio
		expo_text = ExpoText()
		ExpoText.generate(expo_text, e.artist)
		exhibition["text"] = expo_text.text
		full_exhibs.append(exhibition)
		previous_expo_startdate = exhibition["startdate"] # record startdate for next iteration
	return render(request,'past_exhibitions.html', {'full_exhibs': full_exhibs})

def test_exhibition(request):
	artist = Artist()
	Artist.generate(artist)
	exhibition = Exhibition()
	Exhibition.generate(exhibition, artist)
	return render(request,'text_exhibition.html', {'artist_name': artist.name, 'artist_bio': artist.bio, 'expo_title': exhibition.title, 'artist_gender': artist.gender})

def build_json(request):
	google_sheet_url = "https://docs.google.com/spreadsheets/d/1PrD3UqdqmJM_GpTwfN_JSxQjs6TmsxGxVijUHQ4N58Y/edit#gid=6545"
	path = os.path.join(os.path.dirname(blockhaus101_app.__file__), 'json_data')
	found_key = re.search('/d/(.+?)/', google_sheet_url)
	if found_key:
		spreadsheet_key = found_key.group(1)
	xml_url = "https://spreadsheets.google.com/feeds/worksheets/{}/public/full".format(spreadsheet_key)
	file = urllib.request.urlopen(xml_url)
	data = file.read()
	file.close()
	datadict = xmltodict.parse(data)
	index_dict = dict((e["title"]['#text'], e["id"].partition("/full/")[2]) for e in list(datadict.items())[0][1]["entry"])  # Build an index dictionnary with the tab title as key, and as the value, the new tab id by separating the url of the google spreasheet tab in 3 parts around "/full/" and takes the third part (after the "full")
	print(index_dict) # TEST
	try:
		with open(os.path.join(path, 'index.json'), 'w') as outfile:
			outfile.write(json.dumps(index_dict))
		print('Index cache file "index.json" was successfully created!')
	except:
		print('ERROR WHILE TRYING TO CREATE INDEX FILE')
	for key, value in index_dict.items():
		try:
			json_url = "https://spreadsheets.google.com/feeds/list/{}/{}/public/values?alt=json".format(spreadsheet_key, value)
			print(json_url) # TEST
			json_data = requests.get(json_url).json()
			trimmed_json_data = list()
			for e in json_data['feed']['entry'][2:]:
				element = list()
				for k, v in e.items():
					if k.startswith('gsx'):
						element.append(v["$t"])
				trimmed_json_data.append(element)
			with open(os.path.join(path, '{}.json'.format(key)), 'w') as outfile:
				outfile.write(json.dumps(trimmed_json_data))
			print('JSON cache file "{}" was successfully created!'.format(key))
		except:
			print('ERROR WHILE TRYING TO CACHE "{}"'.format(key))
	return HttpResponse('{}'.format("Les fichiers de cache ont été créés !"))

# def test(request):
# 	json_url = 'https://spreadsheets.google.com/feeds/list/1PrD3UqdqmJM_GpTwfN_JSxQjs6TmsxGxVijUHQ4N58Y/oyb70va/public/values?alt=json'
# 	json_data = requests.get(json_url).json()
# 	trimmed_json_data = list()
# 	for e in json_data['feed']['entry'][2:]:
# 		element = list()
# 		for k, v in e.items():
# 			if k.startswith('gsx'):
# 				element.append(v["$t"])
# 		trimmed_json_data.append(element)
# 	print(json.dumps(trimmed_json_data))
	
