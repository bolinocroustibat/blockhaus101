import asyncio
import base64
from datetime import datetime, timedelta
from typing import Literal, Self

from django.core.files.base import ContentFile
from django.db import models

from base_data_app.models.language import Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import GetImgAiAPI
from blockhaus101_app.models.artist import Artist
from blockhaus101_app.models.exhibition_title import ExhibitionTitle
from blockhaus101_app.models.sitesetting import SiteSetting


class Exhibition(models.Model):
    artist = models.ForeignKey(Artist, related_name="exhibitions", on_delete=models.PROTECT)
    startdate = models.DateTimeField("exhibition start date", blank=True, null=True)
    enddate = models.DateTimeField("exhibition end date", blank=True, null=True)
    image1 = models.ImageField(
        "exhibition image 1", upload_to="exhibitions_imgs", blank=True, null=True
    )
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_exhibitions"
        verbose_name = "exposition"

    def __str__(self) -> str:
        exhibition_title = ExhibitionTitle.objects.get(exhibition=self, language__lang="fr")
        return f"{exhibition_title.title} ({self.pk})"

    def create(self, *args, **kwargs):
        super(Exhibition, self).__init__(*args, **kwargs)
        language = Language.objects.get(lang="fr")  # default language
        ExhibitionTitle.objects.create(exhibition=self, language=language)

    def save(self, *args, **kwargs) -> None:
        if not self.startdate or not self.enddate:
            try:
                period = SiteSetting.objects.get().period
            except Exception:
                period = 7
            logger.debug("Trying to save new exhibition...")
            try:
                self.startdate = Exhibition.objects.latest("enddate").enddate
                self.enddate = self.startdate + timedelta(days=period)
                logger.debug(
                    "At least one exhibition already present, exhibition saved according to previous"
                )
            except Exception:
                self.startdate = datetime.now()
                self.enddate = datetime.now() + timedelta(days=period)
                logger.debug("No exhibition found, saving this new one as the first one...")
        super(Exhibition, self).save(*args, **kwargs)

    def generate_image(self, img_format: Literal["png", "jpeg"] = "jpeg") -> ContentFile | None:
        get_imgai_api = GetImgAiAPI()
        discipline: str = self.artist.discipline_text(lang="en")
        img_prompt = f'Generate a photorealistic image of a contemporary {discipline} art exhibition named "{self.title}" with abstract {discipline} works. Don\'t show the artist, but show the artwork(s) or the performance(s) only, in the exhibition room.'
        logger.debug(img_prompt)
        res: dict | None = asyncio.run(
            get_imgai_api.stable_diffusion_xl(prompt=img_prompt, output_format=img_format)
        )
        if res:
            if "error" in res:
                logger.error(f"Error while requesting image generation: {res["error"]}")
                return None
            else:
                cost: float = res["cost"]
                b64_data: str = res["image"]
                now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename: str = f"{now}_{self.artist.name_slug}"
                img_bytes: bytes = base64.b64decode(b64_data, validate=True)
                self.image1 = ContentFile(img_bytes, name=f"{filename}.{img_format}")
                logger.info(
                    f'Image generated for a cost of {cost}$ as "{str(self.image1)}", not saved in DB (yet?)'
                )
                return self.image1
        return None

    @classmethod
    def get_current(cls) -> Self | None:
        """
        Get the exhibition for the current period
        """
        exhibitions = cls.objects.filter(
            startdate__lte=datetime.now(),
            enddate__gte=datetime.now(),
        )
        if len(exhibitions) == 0:
            return None
        else:
            return exhibitions[0]
