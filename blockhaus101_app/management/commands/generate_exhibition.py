from django.core.management.base import BaseCommand

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.models import Artist, ArtistBiography, Exhibition


class Command(BaseCommand):
    help = "Generate new exhibition with artist and biography"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang", dest="lang", default="fr", help='Language code ("fr" or "en")'
        )
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

    def handle(self, *args, **options):
        lang: str = options.get("lang", "fr")
        if lang not in ["fr", "en"]:
            logger.error("Language code doesn't exist")
            raise ValueError
        language = Language.objects.get(lang=lang)

        artist = Artist()
        artist.generate()
        exhibition = Exhibition(artist=artist)
        exhibition_titles: dict = exhibition.generate_titles()
        biography = ArtistBiography(language=language, artist=artist)
        biography.generate(expo_title=exhibition_titles[lang].text)

        logger.info(artist)
        logger.info(biography.text)
        logger.info(exhibition_titles["fr"].text)
        logger.info(exhibition_titles["en"].text)

        if options["save"] or options["img"]:
            artist.save()
            biography.save()
            logger.info("Artist saved in DB with its biography")

            if options["img"]:
                exhibition.generate_image()

            exhibition.save()
            exhibition_titles["fr"].save()
            exhibition_titles["en"].save()
            logger.info("Exhibition saved in DB with its title")
