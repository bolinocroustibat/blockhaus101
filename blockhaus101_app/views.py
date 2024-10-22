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
from blockhaus101_app.models import (
    Artist,
    ArtistBiography,
    Exhibition,
    ExhibitionText,
    ExhibitionTitle,
    SiteSetting,
)


def index(request, lang: str) -> HttpResponse:
    language = Language.objects.get(lang=lang)
    description = SiteSetting.objects.get(language=language).description

    # try to get an exhibition for current period
    exhibition = Exhibition.get_current()

    if exhibition:
        exhibition_title = ExhibitionTitle.objects.get(language=language, exhibition=exhibition)
        artist = exhibition.artist
        logger.debug(
            f'Current exhibition: {artist.name} "{exhibition_title.text}" ({exhibition.pk})'
        )
        biography = ArtistBiography.objects.get(language=language, artist=artist)
        logger.info(
            f'Current exhibition: {artist.name} "{exhibition_title.text}" ({exhibition.pk})'
        )
    else:
        logger.debug("There is no current exhibition.")

        artist = Artist()
        artist.generate()
        artist.save()
        logger.debug(f'New artist "{artist.name}" has been created in DB')

        exhibition = Exhibition(artist=artist)
        exhibition.save()
        exhibition_title_fr, exhibition_title_en = exhibition.generate()
        exhibition_title_fr.save()
        exhibition_title_en.save()
        exhibition_title = ExhibitionTitle.objects.get(
            language=language, exhibition=exhibition
        )  # Get the title in the current language
        exhibition.generate_image()
        exhibition.save()
        logger.debug(
            f'New exhibition "{exhibition_title_fr.text}" ({exhibition.pk}) has been created in DB'
        )

        biography = ArtistBiography(language=language, artist=artist)
        biography.generate(expo_title=exhibition_title.text)
        biography.save()
        logger.debug(f'New artist biography "{biography.text}" has been created in DB')

    expo_text = ExhibitionText(language=language, exhibition=exhibition, ip=get_client_ip(request))
    expo_text.generate()
    expo_text.save()

    return render(
        request,
        f"{lang}/index.html",
        {
            "lang": lang,
            "description": description,
            "expo_startdate": format_date(exhibition.startdate.date(), format="long", locale=lang),
            "expo_enddate": format_date(exhibition.enddate.date(), format="long", locale=lang),
            "artist_name": artist.name,
            "artist_bio": biography.text,
            "expo_title": exhibition_title.text,
            "expo_text": expo_text.text,
            "expo_image1": exhibition.image1.url if exhibition.image1 else None,
            "artist_gender": artist.gender,
        },
    )


def exhibition(request, slug: str) -> HttpResponse:
    try:
        # get expo + artist from database from expo slug
        expo_text = ExhibitionText.objects.get(slug=slug)
        language = expo_text.language
        description = SiteSetting.objects.get(language=language).description
        lang: str = language.lang
        exhibition = expo_text.exhibition
        exhibition_title = ExhibitionTitle.objects.get(language, exhibition)
        artist = exhibition.artist
        biography = ArtistBiography(language, artist)
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
                "artist_bio": biography.text,
                "expo_title": exhibition_title.text,
                "expo_text": expo_text.text,
                "expo_image1": exhibition.image1.url if exhibition.image1 else None,
                "artist_gender": artist.gender,
            },
        )
    except ExhibitionText.DoesNotExist:
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
        exhibition["title"] = ExhibitionTitle.objects.get(language=language, exhibition=e).text
        exhibition["name"] = e.artist.name
        # Get the artist biography for each exhibition
        biography = ArtistBiography.objects.get(language=language, artist=e.artist)
        exhibition["bio"] = biography.text
        # Get an existing text for each exhibition
        expo_text = ExhibitionText.objects.filter(language=language, exhibition=e).first()
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
