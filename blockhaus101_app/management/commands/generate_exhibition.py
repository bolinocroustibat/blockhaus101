from django.core.management.base import BaseCommand

from base_data_app.models import Language
from blockhaus101_app.models import Artist, Exhibition


class Command(BaseCommand):
    help = "Generate new artist and save in the DB"

    def handle(self, *args, **options):
        language = Language.objects.get(lang="fr")
        artist = Artist(language=language)
        artist.generate()
        artist.save()
        print(artist)
        exhibition = Exhibition(language=language, artist=artist)
        exhibition.generate()
        exhibition.save()
        print(exhibition)
