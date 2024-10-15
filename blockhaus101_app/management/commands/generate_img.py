from django.core.management.base import BaseCommand

from blockhaus101.settings import logger
from blockhaus101_app.models import Exhibition


class Command(BaseCommand):
    help = "Generate an image for an existing exhibition, from its ID"

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            dest="id",
            default=None,
            help="Exhibition ID",
        )

        parser.add_argument(
            "--save",
            default=False,
            action="store_true",
            help="Save into the database",
        )

    def handle(self, *args, **options):
        exhibition = Exhibition.objects.get(pk=options["id"])

        exhibition.generate_image()

        if options["save"]:
            exhibition.save()
            logger.info("Exhibition with image saved in DB")
