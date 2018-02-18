from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from blockhaus101_app.models import *

class Command(BaseCommand):
	help = 'Generate new artist and save in the BDD'

	def handle(self, *args, **options):
		pass