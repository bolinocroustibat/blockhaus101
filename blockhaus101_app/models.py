from django.db import models

class ArtistStored(models.Model):
	name = models.CharField("Artist name", max_length=80)
	GENDER_CHOICES =(
		('f', 'female'),
		('m', 'male')
	)
	gender = models.CharField("Gender", max_length=6, choices=GENDER_CHOICES)
	disclipline = models.CharField("Discipline", max_length=1000)
	bio = models.CharField("Biography", max_length=2000)
	startdate = models.DateTimeField("Date of website beginning appearance")
	enddate = models.DateTimeField("Date of website end of appearance")
	def __str__(self):
		return (self.name)

class ExpoStored(models.Model):
	name = models.CharField("Exhibition title", max_length=80)
	body = models.TextField("Exhibition text", max_length=3000)
	artist = models.ForeignKey(ArtistStored, related_name="expo_artist", on_delete="PROTECT")
	def __str__(self):
		return (self.name)
