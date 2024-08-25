import asyncio
from datetime import datetime
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import GetImgAiAPI, decode_b64_img, save_b64_img
from blockhaus101_app.models import Artist, Exhibition


class Command(BaseCommand):
    help = "Generate new artist and save in the DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang", dest="lang", default="fr", help='Language code ("fr" or "en")'
        )
        parser.add_argument(
            "--img",
            dest="img",
            default=True,
            help="Generate an image of the exhibition using generate AI API",
        )
        parser.add_argument(
            "--save",
            dest="save",
            default=False,
            help="Save into the database",
        )

    def handle(self, *args, **options):
        lang: str = options.get("lang", "fr")
        if lang not in ["fr", "en"]:
            logger.error("Language code doesn't exist")
            raise ValueError

        img: bool = True
        if options.get("img") in ["False", False]:
            img = False

        save: bool = False
        if options.get("save") in ["True", True]:
            save = True

        language = Language.objects.get(lang=lang)

        artist = Artist(language=language)
        artist.generate()

        exhibition = Exhibition(language=language, artist=artist)
        exhibition.generate()

        artist.generate_biography(expo_title=exhibition.title)

        logger.info(artist)
        logger.info(exhibition)

        if img:
            self._generate_image(exhibition)

        if save:
            artist.save()
            logger.info("Artist saved in DB with its biography")
            exhibition.save()
            logger.info("Exhibition saved in DB")

    def _generate_image(self, exhibition: Exhibition) -> None:
        get_imgai_api = GetImgAiAPI()
        img_prompt = "Generate a photorealistic image of an artwork"
        res: dict | None = asyncio.run(get_imgai_api.stable_diffusion_xl(prompt=img_prompt))
        if res:
            cost: float = res["cost"]
            img_b64_data: str = res["image"]
            filename: str = (
                f"{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{exhibition.artist.name_slug}"
            )
            filepath: Path = save_b64_img(img_b64_data, filename)
            exhibition.image1 = decode_b64_img(img_b64_data)
            exhibition.save()
            logger.info(f"Image generated for a cost of {cost}$ and saved in {filepath}")
