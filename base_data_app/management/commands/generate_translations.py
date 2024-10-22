from django.core.management.base import BaseCommand
from googletrans import Translator

from base_data_app.models import Data, DataType, Language
from blockhaus101.settings import logger


class Command(BaseCommand):
    help = "Generate translations for a specific data type"

    def add_arguments(self, parser):
        parser.add_argument(
            "--translate",
            dest="translate",
            default=True,
            action="store_true",
            help="Translate or keep original",
        )
        parser.add_argument(
            "--lang", dest="dest_lang", default="en", help="Destination language code"
        )
        parser.add_argument(
            "--type",
            dest="data_type",
            help="Data type name to translate",
        )
        parser.add_argument(
            "--save",
            dest="save",
            default=False,
            action="store_true",
            help="Save into the database",
        )

    def handle(self, *args, **options):
        if options["dest_lang"] not in ["fr", "en"]:
            logger.error("Destination language code doesn't exist")
            raise ValueError

        dest_language = Language.objects.get(lang=options["dest_lang"])

        data_type = DataType.objects.get(name=options["data_type"])

        for d in Data.objects.filter(data_type=data_type):
            if options["translate"]:
                translator = Translator()
                new_text: str = translator.translate(
                    d.text, src="fr", dest=options["dest_lang"]
                ).text
            else:
                new_text: str = d.text

            if not Data.objects.filter(language=dest_language, text=new_text):
                new_d = Data(
                    data_type=data_type,
                    text=new_text,
                    language=dest_language,
                    translation=d,
                    position=d.position,
                )
                logger.info(f'"{d}" ({d.pk}) of type "{data_type}" translated into "{new_d}"')

                if options["save"]:
                    new_d.save()
                    logger.info(f"...and saved in DB ({new_d.pk})")

            else:
                logger.warning(
                    f'"{new_text}" of type "{data_type}" in language "{dest_language}" already exists in DB'
                )

        logger.info("Finished!")
