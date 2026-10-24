import asyncio
import base64
from datetime import datetime, timedelta
from typing import Literal, Self

import niquests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models

from base_data_app.models.data import Data
from base_data_app.models.language import Language
from blockhaus101.settings import (
    GETIMGAPI_PROMPTS,
    IMAGE_PROVIDER,
    PERIOD,
    logger,
)
from blockhaus101_app.helpers import (
    GetImgAiAPI,
    OpenAiAPI,
    correct_text,
    replace_text,
    replace_text_translations,
)
from blockhaus101_app.models.exhibition_title import ExhibitionTitle


class Exhibition(models.Model):
    artist = models.ForeignKey("Artist", related_name="exhibitions", on_delete=models.CASCADE)
    startdate = models.DateTimeField("exhibition start date", blank=True, null=True)
    enddate = models.DateTimeField("exhibition end date", blank=True, null=True)
    image1 = models.ImageField(
        "exhibition image 1", upload_to="exhibitions_imgs", blank=True, null=True
    )
    image2 = models.ImageField(
        "exhibition image 2", upload_to="exhibitions_imgs", blank=True, null=True
    )
    location = models.CharField(
        "exhibition location", max_length=32, choices=settings.LOCATIONS, blank=True, null=True
    )
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_exhibitions"
        verbose_name = "exposition"

    def __str__(self) -> str:
        if self.pk is None:
            return "Exhibition (unsaved)"
        try:
            exhibition_title = ExhibitionTitle.objects.get(exhibition=self, language__code="fr")
            return f"{exhibition_title.text} ({self.pk})"
        except ExhibitionTitle.DoesNotExist:
            return f"Exhibition {self.pk} (no title)"

    def generate_titles(self) -> dict[str, ExhibitionTitle]:
        """Generate titles for all languages.
        Returns a dictionary with the language code as key and the ExhibitionTitle object as value."""

        # Generate original French title
        title_structure_fr = Data.choose_random(data_type="expos", lang="fr")
        if not title_structure_fr:
            raise ValueError("Could not find a random French title structure")

        text_fr: str = title_structure_fr.text
        text_fr, used_data = replace_text(text_fr, "fr")
        text_fr = correct_text(text_fr, "fr")
        exhibition_title_fr = ExhibitionTitle(
            language=Language.objects.get(code="fr"), exhibition=self, text=text_fr
        )
        res: dict = {"fr": exhibition_title_fr}

        logger.debug(f"Used data for exhibition title FR: {used_data}")

        # Generate titles for all other languages
        for lg in Language.objects.all().exclude(code="fr"):
            title_structure = Data.objects.get(
                language=lg,
                translation=title_structure_fr,
            )
            text: str = title_structure.text
            text = replace_text_translations(text=text, original_keywords=used_data, lang=lg.code)
            text = correct_text(text, lg.code)
            exhibition_title = ExhibitionTitle(language=lg, exhibition=self, text=text)
            res[lg.code] = exhibition_title

        return res

    def save(self, *args, **kwargs) -> None:
        if not self.startdate or not self.enddate:
            logger.debug("Trying to save new exhibition...")
            try:
                latest_exhibition = Exhibition.objects.latest("enddate")
            except Exhibition.DoesNotExist:
                latest_exhibition = None

            if latest_exhibition and latest_exhibition.enddate:
                self.startdate = latest_exhibition.enddate
                self.enddate = self.startdate + timedelta(days=PERIOD)
                logger.debug(
                    "At least one exhibition already present, exhibition saved according to previous"
                )
            else:
                self.startdate = datetime.now()
                self.enddate = datetime.now() + timedelta(days=PERIOD)
                logger.debug(
                    "No exhibition found or invalid dates, saving this new one as the first one..."
                )
        super().save(*args, **kwargs)

    def generate_image(self, img_format: Literal["png", "jpeg"] = "jpeg") -> ContentFile | None:
        logger.debug(f"Starting image generation for exhibition {self.pk}")
        discipline: str = self.artist.get_discipline(lang="en")
        exhibition_title = ExhibitionTitle.objects.get(language__code="en", exhibition=self)

        specific_prompt = GETIMGAPI_PROMPTS.get(discipline)
        if not specific_prompt:
            logger.error(f"No specific prompt found for discipline {discipline}")
            return None
        img_prompt: str = specific_prompt.format(
            artist_gender={"f": "female", "m": "male"}[self.artist.gender],
            discipline=discipline,
            exhibition_title=exhibition_title.text,
        )
        img_prompt = f"{img_prompt} Photorealistic photo, no text, watermarks, or frames."

        logger.debug(
            f"Sending image generation request via {IMAGE_PROVIDER} with prompt: {img_prompt}"
        )
        img_bytes, cost = self._request_image_bytes(img_prompt, img_format)
        if not img_bytes:
            logger.debug("Image generation failed or returned no images")
            return None

        now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename: str = f"{now}_{self.artist.name_slug}"
        content_file = ContentFile(img_bytes, name=f"{filename}.{img_format}")
        self.image1 = content_file
        cost_label = f"{cost}$" if cost is not None else "unknown"
        logger.info(
            f'Image generated for a cost of {cost_label} as "{self.image1!s}", not saved in DB (yet?)'
        )
        return content_file

    def _request_image_bytes(
        self, img_prompt: str, img_format: Literal["png", "jpeg"]
    ) -> tuple[bytes | None, float | None]:
        if IMAGE_PROVIDER == "openai":
            b64_data, price, error_msg = asyncio.run(
                OpenAiAPI().generate_image(prompt=img_prompt, output_format=img_format)
            )
            if error_msg or not b64_data:
                return None, None
            return base64.b64decode(b64_data, validate=True), price

        res: dict | None = asyncio.run(
            GetImgAiAPI().generate_image(prompt=img_prompt, output_format=img_format)
        )
        if not res or not res.get("url"):
            return None, None

        try:
            response = niquests.get(res["url"], timeout=30)
        except niquests.RequestException as e:
            logger.error(f"Failed to download GetImg image: {e!s}")
            return None, None

        if response.status_code != 200 or not response.content:
            logger.error(f"Failed to download GetImg image: HTTP {response.status_code}")
            return None, None

        return response.content, res.get("cost")

    @classmethod
    def get_current(cls) -> Self | None:
        """
        Get the exhibition for the current period
        """
        exhibitions = cls.objects.filter(startdate__lte=datetime.now(), enddate__gte=datetime.now())
        if len(exhibitions) != 0:
            return exhibitions[0]
        return None
