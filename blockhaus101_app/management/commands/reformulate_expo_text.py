import asyncio

from django.core.management.base import BaseCommand

from blockhaus101.settings import logger
from blockhaus101_app.helpers import OpenAiAPI
from blockhaus101_app.models import ExhibitionText


class Command(BaseCommand):
    help = "Reformulate the text of an existing exhibition, from its ID"

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            dest="id",
            default=None,
            help="Exhibition Text ID",
        )

        parser.add_argument(
            "--save",
            default=False,
            action="store_true",
            help="Save into the database",
        )

    def handle(self, *args, **options):
        exhibition_text = ExhibitionText.objects.get(pk=options["id"])

        logger.info(f"Original text:\n{exhibition_text.text}")

        openai_api = OpenAiAPI()

        (reformulated_text, price, error_msg) = asyncio.run(
            openai_api.reformulate(text=exhibition_text.text)
        )

        if not error_msg:
            logger.info(f"Reformulated text:\n{reformulated_text}")
            logger.info(f"Price: {price}")

            if options["save"] and reformulated_text:
                exhibition_text.text = reformulated_text
                exhibition_text.save()
                logger.info("New exhibition text saved in DB.")

        else:
            logger.error(f"Error: {error_msg}")
