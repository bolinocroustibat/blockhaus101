from datetime import datetime, timedelta
from django.db import models

from blockhaus101_app.helpers.string import logger
from blockhaus101_app.models.artist import Artist
from blockhaus101_app.models.language import Language
from blockhaus101_app.models.sitesetting import SiteSetting


class Exhibition(models.Model):

    language = models.ForeignKey(
        Language, related_name="exhibitions", on_delete=models.PROTECT
    )
    title = models.CharField("exhibition title", max_length=80)
    artist = models.ForeignKey(
        Artist, related_name="exhibitions", on_delete=models.PROTECT
    )
    startdate = models.DateTimeField("exhibition start date", blank=True, null=True)
    enddate = models.DateTimeField("exhibition end date", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockhaus101_exhibitions"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.startdate or not self.enddate:
            try:
                period = SiteSetting.objects.get().period
            except:
                period = 7
            logger.debug("NOW TRYING TO SAVE NEW EXHIBITION...")
            try:
                self.startdate = Exhibition.objects.latest("enddate").enddate
                self.enddate = self.startdate + timedelta(days=period)
                logger.debug(
                    "AT LEAST ONE EXHIBITION ALREADY PRESENT, EXHIBITION SAVED ACCORDING TO PREVIOUS!"
                )
            except:
                self.startdate = datetime.now()
                self.enddate = datetime.now() + timedelta(days=period)
                logger.debug(
                    "NO EXHIBITIONS ALREADY PRESENT, FIRST EXHIBITION TO SAVE!"
                )
        super(Exhibition, self).save(*args, **kwargs)

    def generate(self) -> None:
        self.title = self.artist.create_expo_title()

    @classmethod
    def get_current(cls, lang: str = "fr"):
        """
        Get the exhibition for the current period
        """
        try:
            return cls.objects.filter(
                language__lang=lang,
                startdate__lte=datetime.now(),
                enddate__gte=datetime.now(),
            )[0]
        except Exception as e:
            logger.error(f"There is no current exhibition: {str(e)}")
