"""Unit tests for model helpers that do not call external services."""

from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from base_data_app.models import Data, DataType
from blockhaus101.settings import PERIOD
from blockhaus101_app.models import Artist, Exhibition, ExhibitionText, ExhibitionTitle
from blockhaus101_app.tests.factories import make_artist, make_exhibition, make_language


class TestArtistNameSlug(SimpleTestCase):
    def test_strips_accents_and_lowercases(self) -> None:
        artist = Artist(name="José García")

        self.assertEqual(artist.name_slug, "jose-garcia")

    def test_keeps_hyphens(self) -> None:
        artist = Artist(name="Jean-Luc Ça")

        self.assertEqual(artist.name_slug, "jean-luc-ca")


class TestArtistDiscipline(TestCase):
    def test_returns_the_translation_for_the_requested_language(self) -> None:
        english = make_language("en", "English")
        french = make_language("fr", "French")
        artist = make_artist(language=english, discipline_text="painting")
        Data.objects.create(
            data_type=artist.discipline.data_type,
            text="peinture",
            language=french,
            translation=artist.discipline,
        )

        self.assertEqual(artist.get_discipline(), "painting")
        self.assertEqual(artist.get_discipline("fr"), "peinture")
        self.assertEqual(artist.get_discipline("en"), "painting")

    def test_follows_the_discipline_translation_link(self) -> None:
        english = make_language("en", "English")
        french = make_language("fr", "French")
        data_type, _created = DataType.objects.get_or_create(name="DISCIPLINE")
        english_discipline = Data.objects.create(
            data_type=data_type, text="painting", language=english
        )
        french_discipline = Data.objects.create(
            data_type=data_type,
            text="peinture",
            language=french,
            translation=english_discipline,
        )
        artist = Artist.objects.create(name="Ada", gender="f", discipline=french_discipline)

        self.assertEqual(artist.get_discipline("en"), "painting")


class TestExhibitionDates(TestCase):
    def test_first_exhibition_starts_now_and_lasts_one_period(self) -> None:
        artist = make_artist()
        before = datetime.now()
        exhibition = Exhibition(artist=artist)
        exhibition.save()
        after = datetime.now()

        self.assertIsNotNone(exhibition.startdate)
        self.assertIsNotNone(exhibition.enddate)
        assert exhibition.startdate is not None
        assert exhibition.enddate is not None
        self.assertGreaterEqual(exhibition.startdate, before)
        self.assertLessEqual(exhibition.startdate, after)
        # save() reads the clock twice, so the span can be a fraction of a second off
        span = exhibition.enddate - exhibition.startdate
        self.assertAlmostEqual(
            span.total_seconds(), timedelta(days=PERIOD).total_seconds(), delta=2
        )

    def test_next_exhibition_starts_when_the_previous_one_ends(self) -> None:
        artist = make_artist()
        previous_end = datetime(2024, 1, 8, 12, 0, 0)
        make_exhibition(
            artist,
            startdate=datetime(2024, 1, 1, 12, 0, 0),
            enddate=previous_end,
        )

        exhibition = Exhibition(artist=artist)
        exhibition.save()

        self.assertEqual(exhibition.startdate, previous_end)
        self.assertEqual(exhibition.enddate, previous_end + timedelta(days=PERIOD))

    def test_keeps_dates_that_were_already_set(self) -> None:
        artist = make_artist()
        start = datetime(2020, 5, 1, 9, 0, 0)
        end = datetime(2020, 5, 8, 9, 0, 0)
        exhibition = make_exhibition(artist, startdate=start, enddate=end)

        self.assertEqual(exhibition.startdate, start)
        self.assertEqual(exhibition.enddate, end)


class TestExhibitionCurrent(TestCase):
    def test_returns_the_exhibition_covering_now(self) -> None:
        artist = make_artist()
        now = datetime.now()
        current = make_exhibition(
            artist,
            startdate=now - timedelta(days=1),
            enddate=now + timedelta(days=1),
        )
        make_exhibition(
            artist,
            startdate=now - timedelta(days=20),
            enddate=now - timedelta(days=10),
        )
        make_exhibition(
            artist,
            startdate=now + timedelta(days=10),
            enddate=now + timedelta(days=20),
        )

        self.assertEqual(Exhibition.get_current(), current)

    def test_returns_none_when_nothing_is_current(self) -> None:
        artist = make_artist()
        now = datetime.now()
        make_exhibition(
            artist,
            startdate=now - timedelta(days=20),
            enddate=now - timedelta(days=10),
        )

        self.assertIsNone(Exhibition.get_current())


class TestExhibitionString(TestCase):
    def test_uses_the_french_title(self) -> None:
        french = make_language("fr", "French")
        artist = make_artist()
        exhibition = make_exhibition(
            artist,
            startdate=datetime(2024, 1, 1),
            enddate=datetime(2024, 1, 8),
        )
        ExhibitionTitle.objects.create(
            language=french, exhibition=exhibition, text="Oiseaux de verre"
        )

        self.assertEqual(str(exhibition), f"Oiseaux de verre ({exhibition.pk})")

    def test_unsaved_exhibition_skips_the_title_lookup(self) -> None:
        self.assertEqual(str(Exhibition()), "Exhibition (unsaved)")

    def test_reports_a_missing_title(self) -> None:
        artist = make_artist()
        exhibition = make_exhibition(
            artist,
            startdate=datetime(2024, 1, 1),
            enddate=datetime(2024, 1, 8),
        )

        self.assertEqual(str(exhibition), f"Exhibition {exhibition.pk} (no title)")


class TestExhibitionTextSlug(TestCase):
    def setUp(self) -> None:
        self.french = make_language("fr", "French")
        self.artist = make_artist(name="Ada Lovelace")
        self.exhibition = make_exhibition(
            self.artist,
            startdate=datetime(2024, 1, 1),
            enddate=datetime(2024, 1, 8),
        )
        self.title = ExhibitionTitle.objects.create(
            language=self.french,
            exhibition=self.exhibition,
            text="Glass birds",
        )

    def _save_text(self, body: str) -> ExhibitionText:
        text = ExhibitionText(language=self.french, exhibition=self.exhibition, text=body)
        text.save()
        return text

    def test_builds_a_slug_from_the_artist_and_the_title(self) -> None:
        text = self._save_text("A short text")

        self.assertEqual(text.slug, "ada-lovelace-glass-birds")

    def test_appends_a_number_when_the_slug_is_taken(self) -> None:
        self._save_text("First")
        second = self._save_text("Second")

        self.assertEqual(second.slug, "ada-lovelace-glass-birds-2")

    def test_skips_saving_after_too_many_slug_collisions(self) -> None:
        for index in range(10):
            saved = self._save_text(f"Text {index}")
            self.assertIsNotNone(saved.pk)

        extra = self._save_text("One too many")

        self.assertIsNone(extra.pk)
        self.assertEqual(ExhibitionText.objects.count(), 10)


class TestDataSelection(TestCase):
    def test_returns_none_when_nothing_matches(self) -> None:
        self.assertIsNone(Data.choose_random("MISSING"))
        self.assertIsNone(Data.choose_random_excluding("MISSING", lang="fr"))

    def test_includes_entries_with_no_language(self) -> None:
        make_language("fr", "French")
        english = make_language("en", "English")
        color_type = DataType.objects.create(name="COLOR")
        Data.objects.create(data_type=color_type, text="only-en", language=english)
        Data.objects.create(data_type=color_type, text="no-lang", language=None)

        chosen = Data.choose_random("COLOR", lang="fr")

        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen.text, "no-lang")

    def test_does_not_pick_an_entry_that_was_already_used(self) -> None:
        french = make_language("fr", "French")
        color_type = DataType.objects.create(name="COLOR")
        Data.objects.create(data_type=color_type, text="red", language=french)
        Data.objects.create(data_type=color_type, text="blue", language=french)
        sequence = iter(["red", "red", "blue"])

        def fake_choices(entries: list[Data], weights: list[int]) -> list[Data]:
            wanted = next(sequence)
            match = next(entry for entry in entries if entry.text == wanted)
            return [match]

        with patch("base_data_app.models.data.choices", side_effect=fake_choices):
            first, used = Data.choose_random_excluding("COLOR", lang="fr") or (None, [])
            second, used = Data.choose_random_excluding("COLOR", lang="fr", excluding=used) or (
                None,
                used,
            )

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None
        assert second is not None
        self.assertEqual(first.text, "red")
        self.assertEqual(second.text, "blue")
        self.assertEqual([item.text for item in used], ["red", "blue"])
