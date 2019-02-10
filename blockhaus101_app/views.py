from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.core.mail import send_mail
from datetime import datetime, timedelta
import tweepy

import blockhaus101_app
from .models import *
from .forms import FormContact
from .utils import logger, get_client_ip, build_cache
from blockhaus101.settings import GOOGLE_SHEET_URL


def index(request):
	try: # try to get an artist for current period
		# artist = (Artist.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
		# expo_title = ExpoTitle.objects.filter(artist=artist) # in case we also want a fixes title, do something like that
		exhibition = (Exhibition.objects.filter(startdate__lte=datetime.now()).filter(enddate__gte=datetime.now()))[0]
		artist = Artist.objects.filter(artist_exhibition=exhibition)[0]
		logger.info('CURRENT EXHIBITION DISPLAYED : {} "{}"'.format(artist.name, exhibition.title))
	except:
		logger.debug("THERE IS NO CURRENT EXHIBITION IN THE TIME RANGE")
		artist = Artist()
		artist.generate()
		artist.save()
		logger.debug('NEW ARTIST "{}" HAS BEEN GENERATED AND SAVED'.format(artist.name))
		exhibition = Exhibition()
		exhibition.artist = artist
		exhibition.generate()
		exhibition.save()
		logger.debug('NEW EXHIBITION "{}" HAS BEEN GENERATED AND SAVED'.format(exhibition.title))
	expo_text = ExpoText()
	expo_text.exhibition = exhibition
	ip = get_client_ip(request)
	expo_text.generate(ip)
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
		logger.error('Exhibition not found.')
		raise Http404("Cette expo n'existe pas")


# def manifesto(request):
# 	try:
# 		manifesto_text = SiteSettings.objects.get().manifesto
# 	except:
# 		manifesto_text = ""
# 	return render(request,'manifeste.html', {'manifesto_text': manifesto_text})


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
		expo_text.exhibition = e
		expo_text.generate()
		exhibition["text"] = expo_text.text
		full_exhibs.append(exhibition)
		previous_expo_startdate = exhibition["startdate"] # record startdate for next iteration
	return render(request,'past-exhibitions.html', {'full_exhibs': full_exhibs})


def pratique(request):
	form = FormContact(request.POST or None)
	message = None
	if request.method == 'POST': # Checks to see if we get a POST back...
		if form.is_valid(): # Checks to see form is valid
			send_mail(
				subject = 'Mail envoyé depuis le site Blockhaus101',
				message ='Expéditeur : ' + form.cleaned_data['name'] + ' / E-mail expéditeur : ' + form.cleaned_data['email'] + ' / Téléphone expéditeur : ' + form.cleaned_data['phone'] + ' / Texte du message : ' + form.cleaned_data['text'],
				from_email = form.cleaned_data['email'],
				recipient_list = ['moi@adriencarpentier.com'],
				fail_silently=False,
				html_message = 'Expéditeur : ' + form.cleaned_data['name'] + ' <br/> E-mail expéditeur : '+form.cleaned_data['email']+' <br/> Téléphone expéditeur : ' + form.cleaned_data['phone'] + ' <br/> Texte du message : '+form.cleaned_data['text']
			)
			form = FormContact()
			logger.info("Email de contact envoyé !")
			message ="Votre demande a bien été envoyée. Nous vous tiendrons au courant dans les plus brefs délais."
		else:
			logger.warning("Formulaire non valide")
			message ="Votre demande n'a pas été envoyé, vérifiez que tous les champs ont été remplis."
	return render(request,'infos-pratiques.html', {'form_contact': form, 'message': message})


def build_json(request):
	build_cache(GOOGLE_SHEET_URL)
	return HttpResponse('{}'.format("Les fichiers de cache ont été créés !"))

