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
            help="Translate or keep original",
        )
        parser.add_argument(
            "--lang", dest="dest_lang", default="en", help="Destination language code"
        )
        parser.add_argument(
            "--type",
            dest="data_type",
            help="Date type to translate",
        )
        parser.add_argument(
            "--save",
            dest="save",
            default=False,
            help="Save into the database",
        )

    def handle(self, *args, **options):
        translate: bool = True
        if options.get("translate") in ["False", False]:
            translate = False

        dest_lang: str = options.get("lang", "en")

        save: bool = False
        if options.get("save") in ["True", True]:
            save = True

        if dest_lang not in ["fr", "en"]:
            logger.error("Destination language code doesn't exist")
            raise ValueError

        dest_language = Language.objects.get(lang=dest_lang)

        data_type = DataType.objects.get(name=options["data_type"])

        for d in Data.objects.filter(data_type=data_type):
            if translate:
                translator = Translator()
                new_text: str = translator.translate(d.text, src="fr", dest=dest_lang).text
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
                logger.info(f'"{d}" of type "{data_type}" translated into "{new_d}"')

                if save:
                    new_d.save()
                    logger.info("...and saved in DB")

            else:
                logger.warning(
                    f'"{new_text}" of type "{data_type}" in language "{dest_language}" already exists in DB'
                )

        logger.info("Finished!")
