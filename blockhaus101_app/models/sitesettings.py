from django.db import models
from .language import Language


class SiteSettings(models.Model):

	language = models.ForeignKey(
		Language, related_name="language_sitesettings", on_delete=models.PROTECT
	)
	description = models.TextField("site header text", max_length=1000, default="")
	period = models.IntegerField("period between two exhibitions, in days", default=7)

	class Meta:
		db_table = "blockhaus101_settings"
		verbose_name = "General setting"

	def __str__(self) -> str:
		return "Settings {}".format(self.lang)
