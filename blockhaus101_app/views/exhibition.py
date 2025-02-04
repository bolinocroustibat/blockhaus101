from babel.dates import format_date
from django.http import Http404, HttpResponse
from django.shortcuts import render

from blockhaus101.settings import logger
from blockhaus101_app.models import (
    ArtistBiography,
    ExhibitionText,
    ExhibitionTitle,
)


def exhibition(request, slug: str) -> HttpResponse:
    try:
        # get expo + artist from database from expo slug
        expo_text = ExhibitionText.objects.get(slug=slug)
        language = expo_text.language
        exhibition = expo_text.exhibition
        exhibition_title = ExhibitionTitle.objects.get(language, exhibition)
        artist = exhibition.artist
        biography = ArtistBiography(language, artist)
        return render(
            request,
            f"{language.code}/index.html",
            {
                "lang": language.code,
                "expo_startdate": format_date(
                    exhibition.startdate.date(), format="long", locale=language.code
                ),
                "expo_enddate": format_date(
                    exhibition.enddate.date(), format="long", locale=language.code
                ),
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
