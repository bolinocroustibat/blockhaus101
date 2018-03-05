from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
import os
import re
import requests
import urllib
import xmltodict
import json
from datetime import datetime, timedelta
from collections import OrderedDict



json_url = "https://spreadsheets.google.com/feeds/list/1PrD3UqdqmJM_GpTwfN_JSxQjs6TmsxGxVijUHQ4N58Y/oqni9wn/public/values?alt=json"
print(json_url) # TEST
json_data = requests.get(json_url).json(object_pairs_hook=OrderedDict)

print(type(json_data))

trimmed_json_data = list()
for e in json_data['feed']['entry'][2:]:
	print(e)
	element = list()
	for k, v in e.items():
		if k.startswith('gsx'):
			element.append(v["$t"])
	trimmed_json_data.append(element)
#print(trimmed_json_data)

