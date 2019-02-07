from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from blockhaus101_app.models import *

class Command(BaseCommand):
	help = 'Generate new artist and save in the BDD'

	def handle(self, *args, **options):
		artist = Artist()
		Artist.generate(artist)
		artist.save()
		exhibition = Exhibition()
		exhibition.artist = artist
		exhibition.generate()
		exhibition.save()