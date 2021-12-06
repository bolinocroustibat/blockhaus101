from datetime import datetime, timedelta

from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.core.mail import send_mail

from blockhaus101_app.models import *
from blockhaus101_app.forms import FormContact
from blockhaus101_app.utils import logger, get_client_ip


def index(request, lang: str) -> HttpResponse:
	language = Language.objects.get(lang=lang)
	description = SiteSetting.objects.get(language=language).description
	try:
	# try to get an exhibition for current period
		exhibition = (
			Exhibition.objects.filter(language=language).filter(startdate__lte=datetime.now()).filter(
				enddate__gte=datetime.now()
			)
		)[0]
		artist = Artist.objects.filter(exhibitions=exhibition)[0]
		logger.info(
			'Current exhibition displayed: {} "{}"'.format(
				artist.name, exhibition.title
			)
		)
	except Exception as e:
		logger.debug("There is no current exhibition in the time range")
		artist = Artist(language=language)
		artist.generate()
		artist.save()
		logger.debug('New artist "{}" has been created in DB'.format(artist.name))
		exhibition = Exhibition(language=language)
		exhibition.artist = artist
		exhibition.generate()
		exhibition.save()
		logger.debug(
			'New echibition "{}" has been created in DB'.format(exhibition.title)
		)
	expo_text = ExpoText(language=language, exhibition=exhibition)
	ip = get_client_ip(request)
	expo_text.generate(ip=ip)
	# expo_text.save()
	return render(
		request,
		f"{lang}/index.html",
		{
			"lang": lang,
			"description": description,
			"expo_startdate": exhibition.startdate.date(),
			"expo_enddate": exhibition.enddate.date(),
			"artist_name": artist.name,
			"artist_bio": artist.bio,
			"expo_title": exhibition.title,
			"expo_text": expo_text.text,
			"artist_gender": artist.gender,
		},
	)


def exhibition(request, slug: str) -> HttpResponse:
	try:  # get expo + artist from database from expo slug
		expo_text = ExpoText.objects.get(slug=slug)
		language = expo_text.language
		description = SiteSetting.objects.get(language=language).description
		lang = language.lang
		exhibition = Exhibition.objects.get(exhibition_expotext=expo_text)
		artist = Artist.objects.get(artist_exhibition=exhibition)
		return render(
			request,
			f"{lang}/index.html",
			{
				"lang": lang,
				"description": description,
				"expo_startdate": exhibition.startdate.date(),
				"expo_enddate": exhibition.enddate.date(),
				"artist_name": artist.name,
				"artist_bio": artist.bio,
				"expo_title": exhibition.title,
				"expo_text": expo_text.text,
				"artist_gender": artist.gender,
			},
		)
	except ExpoText.DoesNotExist:
		logger.error("Exhibition not found.")
		raise Http404("Exhibition not found")

# def manifesto(request):
# 	try:
# 		manifesto_text = SiteSetting.objects.get().manifesto
# 	except:
# 		manifesto_text = ""
# 	return render(request,'manifeste.html', {'manifesto_text': manifesto_text})


def past_exhibitions(request, lang: str) -> HttpResponse:
	language = Language.objects.get(lang=lang)
	full_exhibs = list()
	exhibitions = Exhibition.objects.filter(enddate__lte=datetime.now()).order_by(
		"-enddate"
	)  # get all artist with enddate before today
	# 	artists = Artist.objects.filter(enddate__lte=datetime.now()) # get all artist with enddate before today
	for e in exhibitions:
		exhibition = dict()
		exhibition["startdate"] = e.startdate.date()
		try:  # try to get the startdate of most recent exhibition (previous on the loop
			if (
				e.enddate.date() == previous_expo_startdate
			):  # if this startdate is the same day as the enddate
				exhibition["enddate"] = e.enddate.date() - timedelta(
					days=1
				)  # remove one day to the enddate
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
		previous_expo_startdate = exhibition[
			"startdate"
		]  # record startdate for next iteration
	return render(
		request,
		f"{lang}/past-exhibitions.html",
		{
			"lang": lang,
			"full_exhibs": full_exhibs
		}
	)


def contact(request, lang: str) -> HttpResponse:
	language = Language.objects.get(lang=lang)
	form = FormContact(request.POST or None)
	message = None
	if request.method == "POST":  # Checks to see if we get a POST back...
		if form.is_valid():  # Checks to see form is valid
			send_mail(
				subject="Mail from Blockhaus101 website",
				message="Sender: "
				+ form.cleaned_data["name"]
				+ " / Sender email: "
				+ form.cleaned_data["email"]
				+ " / Sender phone: "
				+ form.cleaned_data["phone"]
				+ " / Message text: "
				+ form.cleaned_data["text"],
				from_email=form.cleaned_data["email"],
				recipient_list=["moi@adriencarpentier.com"],
				fail_silently=False,
				html_message="Expéditeur : "
				+ form.cleaned_data["name"]
				+ " <br/> Sender email: "
				+ form.cleaned_data["email"]
				+ " <br/> Sender phone: "
				+ form.cleaned_data["phone"]
				+ " <br/> Message text: "
				+ form.cleaned_data["text"],
			)
			form = FormContact()
			logger.info("Contact email sent!")
			message = "Votre demande a bien été envoyée. Nous vous tiendrons au courant dans les plus brefs délais."
		else:
			logger.warning("Form is not valid")
			message = "Votre demande n'a pas été envoyé, vérifiez que tous les champs ont été remplis."
	return render(
		request,
		f"{lang}/contact.html",
		{
			"lang": lang,
			"form_contact": form,
			"message": message
		}
	)
