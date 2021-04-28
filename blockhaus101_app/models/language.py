from django.db import models


class Language(models.Model):
	LANGUAGE_CHOICES = (("en", "English"), ("fr", "French"))
	language = models.CharField(
		"language", max_length=2, choices=LANGUAGE_CHOICES, default="fr"
	)

	def __str__(self):
		return self.get_language_display()
