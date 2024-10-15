from django.core.management.base import BaseCommand

from blockhaus101.settings import logger
from blockhaus101_app.models import Exhibition


class Command(BaseCommand):
    help = "Generate images for all existing exhibitions which have no image already"

    def add_arguments(self, parser):
        parser.add_argument(
            "--save",
            default=True,
            action="store_true",
            help="Save into the database",
        )

    def handle(self, *args, **options):
        for e in Exhibition.objects.all().order_by("-startdate"):
            if not e.image1:
                e.generate_image()
                if options["save"]:
                    e.save()
                    logger.info(f"Exhibition {e} with image saved in DB")
