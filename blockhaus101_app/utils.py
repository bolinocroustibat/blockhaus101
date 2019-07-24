import logging
import blockhaus101_app

import os
import xmltodict
import re
import urllib
import json
import requests
from collections import OrderedDict

# Project logger
logger = logging.getLogger('blockhaus101')

# # Auth logging for fail2ban
# authlogger = logging.getLogger('auth-logger')
# authlogger.setLevel(logging.WARN)
# handler = logging.handlers.RotatingFileHandler(
# 	'auth.log',
# 	maxBytes=500000,
# 	backupCount=5
# )
# authlogger.addHandler(handler)


def get_client_ip(request):
	""" Give it a Django request, it gives you the client's IP as string. """
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[-1].strip()
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


def build_cache(google_sheet_url):
	if not google_sheet_url:
		logger.error("No Google Docs URL!")
	else:
		try:
			path = os.path.join(os.path.dirname(blockhaus101_app.__file__), 'json_data')
			if not os.path.exists(path):
				logger.debug("Cache folder does not exist, it will be created")
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
			try:
				with open(os.path.join(path, 'index.json'), 'w') as outfile:
					outfile.write(json.dumps(index_dict))
				logger.info('JSON main cache file "index.json" was successfully created!')
			except:
				logger.error('Error while trying to create main cache file "index.json"')
			for key, value in index_dict.items():
				try:
					json_url = "https://spreadsheets.google.com/feeds/list/{}/{}/public/values?alt=json".format(spreadsheet_key, value)
					# logger.debug(json_url) # TEST
					json_data = requests.get(json_url).json(object_pairs_hook= OrderedDict)
				except Exception as e:
					logger.error('Error while trying to get data from table {}'.format(value))
				trimmed_json_data = list()
				for e in json_data['feed']['entry'][2:]:
					element = list()
					for k, v in e.items():
						if k.startswith('gsx'):
							element.append(v["$t"])
					trimmed_json_data.append(element)
				try:
					with open(os.path.join(path, '{}.json'.format(key)), 'w') as outfile:
						outfile.write(json.dumps(trimmed_json_data))
					logger.info('JSON cache file "{}.json" was successfully created!'.format(key))
				except:
					logger.error('Error while trying to create cache file for "{}"'.format(key))
		except Exception as e:
			logger.error(e)
