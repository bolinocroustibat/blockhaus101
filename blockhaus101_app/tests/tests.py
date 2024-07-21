from django.test import TestCase

from blockhaus101.settings import logger
from blockhaus101_app.models import Artist, Exhibition
from blockhaus101_app.tweet import generate_tweet


class TestGenerateContent(TestCase):
    artist = Artist()
    exhibition = Exhibition()

    def test_generate_exhibition(self):
        # try to get exhibition for current period
        current_exhibition = Exhibition.get_current(lang="fr")
        if current_exhibition:
            self.exhibition = current_exhibition
            self.artist = Artist.objects.filter(artist_exhibition=self.exhibition)[0]
            logger.info(f'Current exhibition: {self.artist.name} "{self.exhibition.title}"')
        else:
            logger.info("There is no current exhibition.")
        self.artist.generate()
        logger.info(f'New artist "{self.artist.name}" generated')
        self.exhibition.artist = self.artist
        self.exhibition.generate()
        logger.info(f'New exhibition "{self.exhibition.title}" generated')

    def test_generate_tweet(self):
        tweet1 = generate_tweet(
            lang="fr",
            artist=self.artist,
            exhibition=self.exhibition,
            tweet_type="tweets1",
        )
        logger.info(f'Tweet generated: "{tweet1}"')
        assert isinstance(tweet1, str)
        assert len(tweet1) > 10
        assert len(tweet1) <= 280
        tweet2 = generate_tweet(
            lang="fr",
            artist=self.artist,
            exhibition=self.exhibition,
            tweet_type="tweets2",
        )
        logger.info(f'Tweet generated: "{tweet2}"')
        assert isinstance(tweet2, str)
        assert len(tweet2) > 10
        assert len(tweet2) <= 280
