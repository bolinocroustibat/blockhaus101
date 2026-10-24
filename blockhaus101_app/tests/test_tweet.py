"""Unit tests for tweet assembly. Twitter itself is not called."""

from datetime import datetime

from babel.dates import format_date
from django.test import SimpleTestCase, TestCase

from base_data_app.models import Data, DataType
from blockhaus101_app.models import Artist, Exhibition, ExhibitionTitle
from blockhaus101_app.tests.factories import make_artist, make_exhibition, make_language
from blockhaus101_app.tweet import generate_tweet


class TestGenerateTweetValidation(SimpleTestCase):
    def test_rejects_an_unknown_type(self) -> None:
        with self.assertRaisesMessage(ValueError, "Invalid tweet type"):
            generate_tweet(
                lang="fr",
                artist=Artist(),
                exhibition=Exhibition(),
                tweet_type="nope",
            )


class TestGenerateTweet(TestCase):
    def test_requires_a_tweet_template(self) -> None:
        make_language("fr", "French")

        with self.assertRaisesMessage(ValueError, "tweets1"):
            generate_tweet(
                lang="fr",
                artist=Artist(),
                exhibition=Exhibition(),
                tweet_type="tweets1",
            )

    def test_fills_artist_exhibition_and_dates(self) -> None:
        french = make_language("fr", "French")
        artist = make_artist(name="Ada Lovelace", discipline_text="painting", language=french)
        start = datetime(2024, 3, 4, 10, 0, 0)
        end = datetime(2024, 3, 11, 10, 0, 0)
        exhibition = make_exhibition(artist, startdate=start, enddate=end)
        ExhibitionTitle.objects.create(language=french, exhibition=exhibition, text="Oiseaux")
        tweet_type = DataType.objects.create(name="tweets1")
        Data.objects.create(
            data_type=tweet_type,
            language=french,
            text="[SELF] expose [SELFDISCIPLINE] : [EXPO] ([EXPOSTARTDATE] - [EXPOENDDATE])",
        )

        tweet = generate_tweet(
            lang="fr",
            artist=artist,
            exhibition=exhibition,
            tweet_type="tweets1",
        )

        self.assertIn("Ada Lovelace", tweet)
        self.assertIn("painting", tweet)
        self.assertIn("Oiseaux", tweet)
        self.assertIn(format_date(start.date(), format="medium", locale="fr"), tweet)
        self.assertIn(format_date(end.date(), format="medium", locale="fr"), tweet)
        self.assertNotIn("[", tweet)
