from babel.dates import format_date
from django.http import HttpResponse
from django.shortcuts import render

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import get_client_ip, image_size
from blockhaus101_app.helpers.exhibition_text import create_exhibition_texts
from blockhaus101_app.models import (
    Artist,
    ArtistBiography,
    Exhibition,
    ExhibitionText,
    ExhibitionTitle,
)


def index(request, lang: str) -> HttpResponse:
    language = Language.objects.get(code=lang)

    # try to get an exhibition for current period
    exhibition = Exhibition.get_current()

    if exhibition:
        exhibition_title = ExhibitionTitle.objects.get(language=language, exhibition=exhibition)
        artist = exhibition.artist
        logger.debug(
            f'Current exhibition: {artist.name} "{exhibition_title.text}" ({exhibition.pk})'
        )
        bio = ArtistBiography.objects.get(language=language, artist=artist)
        logger.info(
            f'Current exhibition: {artist.name} "{exhibition_title.text}" ({exhibition.pk})'
        )
        expo_text = ExhibitionText.objects.filter(language=language, exhibition=exhibition).last()
        if not expo_text:
            logger.error(
                f"No exhibition text found for exhibition {exhibition.pk} in language {language.code}"
            )

    else:
        logger.debug("There is no current exhibition.")

        # create a new artist
        artist = Artist()
        artist.generate()
        artist.save()
        logger.debug(f'New artist "{artist.name}" has been created in DB')

        # create a new exhibition, its titles on both languages, and image
        exhibition = Exhibition(artist=artist)
        exhibition.save()
        exhibition_titles: dict = exhibition.generate_titles()
        for lg in Language.objects.all():
            exhibition_titles[lg.code].save()
        exhibition.generate_image()
        exhibition.save()
        logger.debug(
            f'New exhibition "{exhibition_titles["fr"].text}" ({exhibition.pk}) has been created in DB'
        )
        # get the title in the current language to be used in the template
        exhibition_title = exhibition_titles[lang]

        # create a new artist biography, using the exhibition title
        bios: dict[str, ArtistBiography] = artist.generate_bios(expo_titles=exhibition_titles)
        for lg in Language.objects.all():
            bios[lg.code].save()
        bio = bios[lang]
        logger.debug(f'New artist biography "{bio.text}" has been created in DB')

        texts = create_exhibition_texts(exhibition, ip=get_client_ip(request))
        expo_text = texts.get(lang)

    image_width, image_height = image_size(exhibition.image1)
    return render(
        request,
        f"{lang}/index.html",
        {
            "lang": lang,
            "expo_startdate": format_date(exhibition.startdate.date(), format="long", locale=lang)
            if exhibition.startdate
            else "",
            "expo_enddate": format_date(exhibition.enddate.date(), format="long", locale=lang)
            if exhibition.enddate
            else "",
            "artist_name": artist.name,
            "artist_bio": bio.text,
            "expo_title": exhibition_title.text,
            "expo_text": expo_text.text
            if expo_text
            else "",  # Handle None case with error already logged
            "expo_image1": exhibition.image1.url if exhibition.image1 else None,
            "expo_image_width": image_width,
            "expo_image_height": image_height,
            "artist_gender": artist.gender,
            "expo_url": exhibition.page_url(lang),
        },
    )
