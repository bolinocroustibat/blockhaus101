from datetime import datetime
from django.db import models

from .artist import Artist
from .language import Language
from .sitesettings import SiteSettings
from ..utils import logger


class Exhibition(models.Model):

	lang = models.ForeignKey(
		Language, related_name="language_exhibition", on_delete=models.PROTECT
	)
	title = models.CharField("exhibition title", max_length=80)
	artist = models.ForeignKey(
		Artist, related_name="artist_exhibition", on_delete=models.PROTECT
	)
	startdate = models.DateTimeField("exhibition start date", blank=True, null=True)
	enddate = models.DateTimeField("exhibition end date", blank=True, null=True)
	created = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:
		return self.title

	def save(self, *args, **kwargs) -> None:
		if not self.startdate or not self.enddate:
			try:
				period = SiteSettings.objects.get().period
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
