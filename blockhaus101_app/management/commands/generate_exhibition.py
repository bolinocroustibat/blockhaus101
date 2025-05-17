from typing import Any

from django.core.management.base import BaseCommand

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.models import Artist, ArtistBiography, Exhibition, ExhibitionTitle


class Command(BaseCommand):
    help = "Generate new exhibition with artist and biography"

    def add_arguments(self, parser):
        parser.add_argument(
            "--img",
            default=False,
            action="store_true",
            help="Generate an image of the exhibition using generate AI API",
        )
        parser.add_argument(
            "--save",
            default=False,
            action="store_true",
            help="Save into the database",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        artist = Artist()
        artist.generate()
        exhibition = Exhibition(artist=artist)
        exhibition_titles: dict[str, ExhibitionTitle] = exhibition.generate_titles()
        bios: dict[str, ArtistBiography] = artist.generate_bios(expo_titles=exhibition_titles)

        logger.info(artist)
        for lg in Language.objects.all():
            logger.info(bios[lg.code].text)
            logger.info(exhibition_titles[lg.code].text)

        if options["save"] or options["img"]:
            artist.save()
            for lg in Language.objects.all():
                bios[lg.code].save()
            logger.info("Artist saved in DB with its biographies")

            if options["img"]:
                exhibition.generate_image()

            exhibition.save()
            for lg in Language.objects.all():
                exhibition_titles[lg.code].save()
            logger.info(
                f"Exhibition saved in DB with its titles. Dates: {exhibition.startdate} to {exhibition.enddate}"
            )
