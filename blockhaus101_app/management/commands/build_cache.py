from django.core.management.base import BaseCommand

from blockhaus101.settings import GOOGLE_SHEET_URL
from blockhaus101_app.utils import build_cache


class Command(BaseCommand):

	help = 'Build JSON cache files from Google Doc'

	def handle(self, *args, **options):
		build_cache(GOOGLE_SHEET_URL)
