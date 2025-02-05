from datetime import datetime

from babel.dates import format_date
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.models import (
    ArtistBiography,
    Exhibition,
    ExhibitionText,
    ExhibitionTitle,
)

EXHIBITIONS_PER_PAGE = 2


def past_exhibitions(request, lang: str) -> HttpResponse:
    language = Language.objects.get(code=lang)
    page_number = request.GET.get("page", 1)  # Get page from query params, default to 1

    # Get all past exhibitions
    exhibitions = Exhibition.objects.filter(enddate__lte=datetime.now()).order_by("-enddate")

    # Create paginator
    paginator = Paginator(exhibitions, EXHIBITIONS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    full_exhibs = []  # Keep the original name since templates use it
    for e in page_obj:
        try:
            exhibition: dict = {}
            if e.startdate and e.enddate:  # Check for None
                exhibition["startdate"] = format_date(
                    e.startdate.date(), format="long", locale=lang
                )
                exhibition["enddate"] = format_date(e.enddate.date(), format="long", locale=lang)

            try:
                exhibition["title"] = ExhibitionTitle.objects.get(
                    language=language, exhibition=e
                ).text
            except ExhibitionTitle.DoesNotExist:
                exhibition["title"] = f"Exhibition {e.pk} (no title)"
                logger.warning(f"No title found for exhibition {e.pk} in language {lang}")

            exhibition["name"] = e.artist.name

            # Get the artist biography
            try:
                biography = ArtistBiography.objects.get(language=language, artist=e.artist)
                exhibition["bio"] = biography.text
            except ArtistBiography.DoesNotExist:
                exhibition["bio"] = ""
                logger.warning(f"No biography found for artist of exhibition {e.pk}")

            # Get the latest text
            expo_text = ExhibitionText.objects.filter(language=language, exhibition=e).last()
            exhibition["text"] = expo_text.text if expo_text else ""

            # Image
            exhibition["image1"] = None
            if e.image1:
                exhibition["image1"] = e.image1.url

            full_exhibs.append(exhibition)

        except Exception as error:
            logger.error(f"Error getting past exhibition info for exhibition {e.pk}: {str(error)}")
            continue

    template_name = (
        f"{lang}/partials/exhibition-batch.html"
        if request.htmx
        else f"{lang}/past-exhibitions.html"
    )

    return render(
        request,
        template_name,
        {
            "lang": lang,
            "full_exhibs": full_exhibs,
            "page_obj": page_obj,
        },
    )
