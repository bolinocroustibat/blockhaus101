from django.core.management.base import BaseCommand

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.models import Artist, ArtistBiography, Exhibition, ExhibitionTitle


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
        exhibition_title = ExhibitionTitle(language=language, exhibition=exhibition)
        exhibition_title.generate()
        biography = ArtistBiography(artist=artist, language=language)
        biography.generate(expo_title=exhibition_title.text, save=False)

        logger.info(artist)
        logger.info(biography.text)
        logger.info(exhibition_title.text)

        if options["save"] or options["img"]:
            artist.save()
            biography.save()
            logger.info("Artist saved in DB with its biography")

            if options["img"]:
                exhibition.generate_image()

            exhibition.save()
            exhibition_title.save()
            logger.info("Exhibition saved in DB with its title")
