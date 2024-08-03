from django.core.management.base import BaseCommand

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.models import Artist, Exhibition


class Command(BaseCommand):
    help = "Generate new artist and save in the DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang", dest="lang", default="fr", help='Language code ("fr" or "en")'
        )
        parser.add_argument(
            "--save",
            dest="save",
            default=False,
            help="Save into the database",
        )

    def handle(self, *args, **options):
        save: bool = False
        if options.get("save") in ["True", True]:
            save = True

        lang: str = options.get("lang", "fr")

        if lang not in ["fr", "en"]:
            logger.error("Language code doesn't exist")
            raise ValueError

        language = Language.objects.get(lang=lang)

        artist = Artist(language=language)
        artist.generate()

        exhibition = Exhibition(language=language, artist=artist)
        exhibition.generate()

        artist.generate_biography(expo_title=exhibition.title)

        logger.info(artist)
        logger.info(exhibition)

        if save:
            artist.save()
            logger.info("Artist saved in DB with its biography")
            exhibition.save()
            logger.info("Exhibition saved in DB")
