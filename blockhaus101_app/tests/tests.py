from django.test import TestCase

from blockhaus101_app.helpers import logger
from blockhaus101_app.models import Artist, Exhibition
from blockhaus101_app.tweet import generate_tweet


class TestGenerateContent(TestCase):

    artist = Artist()
    exhibition = Exhibition()

    def test_generate_exhibition(self):
        try:
            # try to get exhibition for current period
            self.exhibition = Exhibition.get_current(lang="fr")
            self.artist = Artist.objects.filter(artist_exhibition=self.exhibition)[0]
            logger.info(
                f'Current exhibition: {self.artist.name} "{self.exhibition.title}"'
            )
        except Exception as e:
            logger.info("There is no current exhibition.")
        self.artist.generate()
        logger.info(f'New artist "{self.artist.name}" generated')
        self.exhibition.artist = self.artist
        self.exhibition.generate()
        logger.info(f'New exhibition "{self.exhibition.title}" generated')

    def test_generate_tweet(self):
        tweet1 = generate_tweet(
            artist=self.artist, exhibition=self.exhibition, tweet_type="tweet1"
        )
        logger.info(f'Tweet generated: "{tweet1}"')
        assert type(tweet1) == str
        assert len(tweet1) > 10
        assert len(tweet1) <= 280
        tweet2 = generate_tweet(
            artist=self.artist, exhibition=self.exhibition, tweet_type="tweet2"
        )
        logger.info(f'Tweet generated: "{tweet2}"')
        assert type(tweet2) == str
        assert len(tweet2) > 10
        assert len(tweet2) <= 280
