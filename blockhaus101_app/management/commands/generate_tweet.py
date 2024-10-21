from django.core.management.base import BaseCommand

from blockhaus101.settings import logger
from blockhaus101_app.models import Artist, Exhibition
from blockhaus101_app.tweet import generate_tweet, send_tweet


class Command(BaseCommand):
    help = "Generate and send new tweet to Twitter"

    def add_arguments(self, parser):
        parser.add_argument("--lang", dest="lang", default="fr", help="Language code")
        parser.add_argument(
            "--type",
            dest="tweet_type",
            default="tweets1",
            help="Tweet type (tweets1, tweets2)",
        )

    def handle(self, *args, **options):
        # try to get the exhibition for current period
        exhibition = Exhibition.get_current()
        artist = Artist.objects.filter(exhibitions=exhibition)[0]
        logger.info(f'Current exhibition: {artist.name} "{exhibition}"')
        tweet = generate_tweet(
            lang=options["lang"],
            artist=artist,
            exhibition=exhibition,
            tweet_type=options["tweet_type"],
        )
        logger.info(f'Tweet "{tweet}" generated. Now sending it to Twitter...')
        send_tweet(tweet)
