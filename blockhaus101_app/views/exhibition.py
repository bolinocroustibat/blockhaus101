from babel.dates import format_date
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from blockhaus101.settings import logger
from blockhaus101_app.helpers import image_size
from blockhaus101_app.models import (
    ArtistBiography,
    ExhibitionText,
    ExhibitionTitle,
)


def exhibition(request, lang: str, slug: str) -> HttpResponse:
    expo_text = (
        ExhibitionText.objects.filter(slug=slug)
        .select_related("exhibition__artist", "language")
        .last()
    )
    if expo_text is None:
        logger.warning("Exhibition not found")
        raise Http404("Exhibition not found")

    show = expo_text.exhibition
    slugs = show.slugs_by_language()
    translated = slugs.get(lang)
    if expo_text.language.code != lang and translated:
        return redirect("exhibition", lang=lang, slug=translated, permanent=True)

    artist = show.artist
    title = ExhibitionTitle.objects.filter(language__code=lang, exhibition=show).first()
    bio = ArtistBiography.objects.filter(language__code=lang, artist=artist).first()
    image_width, image_height = image_size(show.image1)
    return render(
        request,
        f"{lang}/index.html",
        {
            "lang": lang,
            "expo_startdate": format_date(show.startdate.date(), format="long", locale=lang)
            if show.startdate
            else "",
            "expo_enddate": format_date(show.enddate.date(), format="long", locale=lang)
            if show.enddate
            else "",
            "artist_name": artist.name,
            "artist_bio": bio.text if bio else "",
            "expo_title": title.text if title else "",
            "expo_text": expo_text.text if expo_text.language.code == lang else "",
            "expo_image1": show.image1.url if show.image1 else None,
            "expo_image_width": image_width,
            "expo_image_height": image_height,
            "artist_gender": artist.gender,
            "alternate_slugs": slugs,
        },
    )
