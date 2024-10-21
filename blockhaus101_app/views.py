from datetime import datetime

from babel.dates import format_date
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import render

from base_data_app.models import Language
from blockhaus101.settings import (
    MAIL_ERROR_MESSAGE,
    MAIL_INVALID_MESSAGE,
    MAIL_SUCCESS_MESSAGE,
    logger,
)
from blockhaus101_app.forms import FormContact
from blockhaus101_app.helpers import get_client_ip
from blockhaus101_app.models import Artist, ArtistBiography, Exhibition, ExpoText, SiteSetting


def index(request, lang: str) -> HttpResponse:
    language = Language.objects.get(lang=lang)
    description = SiteSetting.objects.get(language=language).description

    # try to get an exhibition for current period
    exhibition = Exhibition.get_current()

    if exhibition:
        artist = Artist.objects.filter(exhibitions=exhibition).first()
        biography = ArtistBiography.objects.filter(artist=artist, language=language).first()
        logger.info(f'Current exhibition: {artist.name} "{exhibition.title}"')
    else:
        logger.debug("There is no current exhibition.")

        artist = Artist()
        artist.generate(save=True)
        logger.debug(f'New artist "{artist.name}" has been created in DB')

        exhibition = Exhibition()
        exhibition.artist = artist
        exhibition.generate(img=True, save=True)
        logger.debug(f'New exhibition "{exhibition.title}" has been created in DB')

        biography = ArtistBiography(language=language, artist=artist)
        biography.generate(expo_title=exhibition.title, save=True)
        logger.debug(f'New artist biography "{biography.bio}" has been created in DB')

    expo_text = ExpoText(language=language, exhibition=exhibition)
    ip: str = get_client_ip(request)
    expo_text.generate(ip=ip, save=True)

    return render(
        request,
        f"{lang}/index.html",
        {
            "lang": lang,
            "description": description,
            "expo_startdate": format_date(exhibition.startdate.date(), format="long", locale=lang),
            "expo_enddate": format_date(exhibition.enddate.date(), format="long", locale=lang),
            "artist_name": artist.name,
            "artist_bio": biography.bio,
            "expo_title": exhibition.title,
            "expo_text": expo_text.text,
            "expo_image1": exhibition.image1.url if exhibition.image1 else None,
            "artist_gender": artist.gender,
        },
    )


def exhibition(request, slug: str) -> HttpResponse:
    try:
        # get expo + artist from database from expo slug
        expo_text = ExpoText.objects.get(slug=slug)
        language = expo_text.language
        description = SiteSetting.objects.get(language=language).description
        lang = language.lang
        exhibition = expo_text.exhibition
        artist = exhibition.artist
        return render(
            request,
            f"{lang}/index.html",
            {
                "lang": lang,
                "description": description,
                "expo_startdate": format_date(
                    exhibition.startdate.date(), format="long", locale=lang
                ),
                "expo_enddate": format_date(exhibition.enddate.date(), format="long", locale=lang),
                "artist_name": artist.name,
                "artist_bio": artist.bio,
                "expo_title": exhibition.title,
                "expo_text": expo_text.text,
                "expo_image1": exhibition.image1.url if exhibition.image1 else None,
                "artist_gender": artist.gender,
            },
        )
    except ExpoText.DoesNotExist:
        logger.warning("Exhibition not found")
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
    exhibitions = Exhibition.objects.filter(enddate__lte=datetime.now()).order_by("-enddate")
    # # Get all artists with enddate before today
    # artists = Artist.objects.filter(enddate__lte=datetime.now())
    for e in exhibitions:
        exhibition: dict = {}
        exhibition["startdate"] = format_date(e.startdate.date(), format="long", locale=lang)
        exhibition["enddate"] = format_date(e.enddate.date(), format="long", locale=lang)
        exhibition["title"] = e.title
        exhibition["name"] = e.artist.name
        # Get the artist biography for each exhibition
        biography = ArtistBiography.objects.get(language=language, artist=e.artist)
        exhibition["bio"] = biography.bio
        # Get an existing text for each exhibition
        expo_text = ExpoText.objects.filter(language=language, exhibition=e).first()
        if not expo_text:
            expo_text = ExpoText(language=language, exhibition=e)
            expo_text.generate(save=True)
        exhibition["text"] = expo_text.text
        # Image
        exhibition["image1"] = None
        if e.image1:
            exhibition["image1"] = e.image1.url
        full_exhibs.append(exhibition)
    return render(
        request,
        f"{lang}/past-exhibitions.html",
        {"lang": lang, "full_exhibs": full_exhibs},
    )


def contact(request, lang: str) -> HttpResponse:
    form = FormContact(request.POST or None)
    message = None
    if request.method == "POST":  # Checks to see if we get a POST back...
        if form.is_valid():  # Checks to see form is valid
            try:
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
                    recipient_list=["me@adriencarpentier.com"],
                    fail_silently=False,
                    html_message="Sender : "
                    + form.cleaned_data["name"]
                    + " <br/> Sender email: "
                    + form.cleaned_data["email"]
                    + " <br/> Sender phone: "
                    + form.cleaned_data["phone"]
                    + " <br/> Message text: "
                    + form.cleaned_data["text"],
                )
                form = FormContact()
            except Exception as e:
                logger.error(f"Error while sending email: {str(e)}")
                message = MAIL_ERROR_MESSAGE[lang]
            else:
                logger.info("Contact email sent!")
                message = MAIL_SUCCESS_MESSAGE[lang]
        else:
            logger.warning("Form is not valid")
            message = MAIL_INVALID_MESSAGE[lang]
    return render(
        request,
        f"{lang}/contact.html",
        {"lang": lang, "form_contact": form, "message": message},
    )
