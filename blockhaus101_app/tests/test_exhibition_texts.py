"""Tests for bilingual exhibition text creation."""

from datetime import datetime
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from blockhaus101_app.helpers.exhibition_text import create_exhibition_texts
from blockhaus101_app.models import ExhibitionText, ExhibitionTitle
from blockhaus101_app.tests.factories import make_artist, make_exhibition, make_language


class ExhibitionTextFixture(TestCase):
    def setUp(self) -> None:
        self.french = make_language("fr", "French")
        self.english = make_language("en", "English")
        self.artist = make_artist(name="Ada Lovelace", language=self.french)
        self.exhibition = make_exhibition(
            self.artist,
            startdate=datetime(2025, 3, 1),
            enddate=datetime(2025, 3, 8),
        )
        ExhibitionTitle.objects.create(
            language=self.french, exhibition=self.exhibition, text="oiseaux de verre"
        )
        ExhibitionTitle.objects.create(
            language=self.english, exhibition=self.exhibition, text="glass birds"
        )


def _openai_mock(
    *,
    translated: str | None = "A white room.",
    translate_error: str | None = None,
    reformulated: str | None = "Une salle blanche.",
    reformulate_error: str | None = None,
) -> MagicMock:
    api = MagicMock()
    api.model = {"id": "gpt-test"}
    api.translate = AsyncMock(return_value=(translated, 0.01, translate_error))
    api.reformulate = AsyncMock(return_value=(reformulated, 0.02, reformulate_error))
    return api


class TestCreateExhibitionTexts(ExhibitionTextFixture):
    def test_saves_french_and_english(self) -> None:
        french = ExhibitionText(
            language=self.french,
            exhibition=self.exhibition,
            text="Une salle.",
            ip="1.2.3.4",
        )

        with patch(
            "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
            return_value=_openai_mock(),
        ):
            texts = create_exhibition_texts(self.exhibition, french=french, ip="1.2.3.4")

        assert texts["fr"] is not None
        assert texts["en"] is not None
        self.assertEqual(texts["fr"].text, "Une salle.")
        self.assertEqual(texts["en"].text, "A white room.")
        self.assertEqual(texts["en"].ip, "1.2.3.4")
        self.assertEqual(texts["en"].ai_model, "gpt-test")
        self.assertEqual(ExhibitionText.objects.filter(language=self.french).count(), 1)
        self.assertEqual(ExhibitionText.objects.filter(language=self.english).count(), 1)

    def test_keeps_french_when_translation_fails(self) -> None:
        french = ExhibitionText(
            language=self.french,
            exhibition=self.exhibition,
            text="Une salle.",
            ip="1.2.3.4",
        )

        with patch(
            "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
            return_value=_openai_mock(translated=None, translate_error="unavailable"),
        ):
            texts = create_exhibition_texts(self.exhibition, french=french, ip="1.2.3.4")

        assert texts["fr"] is not None
        self.assertIsNotNone(texts["fr"].pk)
        self.assertEqual(texts["fr"].text, "Une salle.")
        self.assertIsNone(texts["en"])
        self.assertEqual(ExhibitionText.objects.filter(language=self.english).count(), 0)

    def test_generates_and_reformulates_french_when_none_is_given(self) -> None:
        def fake_generate(text: ExhibitionText) -> None:
            text.text = "Texte généré."

        with (
            patch.object(ExhibitionText, "generate", fake_generate),
            patch(
                "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
                return_value=_openai_mock(),
            ),
        ):
            texts = create_exhibition_texts(self.exhibition, ip="9.9.9.9")

        assert texts["fr"] is not None
        assert texts["en"] is not None
        self.assertEqual(texts["fr"].text, "Une salle blanche.")
        self.assertEqual(texts["fr"].ip, "9.9.9.9")
        self.assertEqual(texts["en"].text, "A white room.")

    def test_reuses_an_existing_english_text(self) -> None:
        french = ExhibitionText.objects.create(
            language=self.french, exhibition=self.exhibition, text="Une salle."
        )
        existing = ExhibitionText.objects.create(
            language=self.english, exhibition=self.exhibition, text="Already there."
        )
        api = _openai_mock()

        with patch("blockhaus101_app.helpers.exhibition_text.OpenAiAPI", return_value=api):
            texts = create_exhibition_texts(self.exhibition, french=french)

        self.assertEqual(texts["en"], existing)
        api.translate.assert_not_called()


class TestGenerateEnglishTextsCommand(ExhibitionTextFixture):
    def _older_show(self) -> None:
        older = make_exhibition(
            self.artist,
            startdate=datetime(2024, 6, 1),
            enddate=datetime(2024, 6, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=older, text="avant")
        ExhibitionText.objects.create(
            language=self.french, exhibition=older, text="Texte trop ancien."
        )

    def test_dry_run_lists_shows_and_does_not_call_openai(self) -> None:
        ExhibitionText.objects.create(
            language=self.french, exhibition=self.exhibition, text="Une salle blanche."
        )
        self._older_show()
        skipped = make_exhibition(
            self.artist,
            startdate=datetime(2025, 4, 1),
            enddate=datetime(2025, 4, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=skipped, text="vide")

        api = _openai_mock()
        out = StringIO()
        with patch("blockhaus101_app.helpers.exhibition_text.OpenAiAPI", return_value=api):
            call_command("generate_english_texts", stdout=out)

        text = out.getvalue()
        self.assertIn("Looking for French texts to translate from 2025-01-01", text)
        self.assertIn("To translate: 1", text)
        self.assertIn("Skipped, no French text: 1", text)
        self.assertIn("Une salle blanche.", text)
        self.assertIn("Dry run.", text)
        self.assertNotIn("Texte trop ancien.", text)
        api.translate.assert_not_called()
        self.assertEqual(ExhibitionText.objects.filter(language=self.english).count(), 0)

    def test_save_writes_the_english_text(self) -> None:
        ExhibitionText.objects.create(
            language=self.french, exhibition=self.exhibition, text="Une salle blanche."
        )
        self._older_show()

        out = StringIO()
        with patch(
            "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
            return_value=_openai_mock(),
        ):
            call_command("generate_english_texts", "--save", stdout=out)

        self.assertIn("Saved 1 English text(s). Failed: 0.", out.getvalue())
        english = ExhibitionText.objects.get(language=self.english)
        self.assertEqual(english.text, "A white room.")
        self.assertEqual(english.exhibition, self.exhibition)

    def test_save_skips_shows_that_already_have_english(self) -> None:
        ExhibitionText.objects.create(
            language=self.french, exhibition=self.exhibition, text="Une salle blanche."
        )
        ExhibitionText.objects.create(
            language=self.english, exhibition=self.exhibition, text="Already there."
        )

        out = StringIO()
        with patch(
            "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
            return_value=_openai_mock(),
        ) as api_cls:
            call_command("generate_english_texts", "--save", stdout=out)

        self.assertIn("Skipped, English already present: 1", out.getvalue())
        self.assertIn("Saved 0 English text(s).", out.getvalue())
        api_cls.assert_not_called()
        self.assertEqual(ExhibitionText.objects.get(language=self.english).text, "Already there.")

    def test_from_limits_the_shows(self) -> None:
        ExhibitionText.objects.create(
            language=self.french, exhibition=self.exhibition, text="Une salle blanche."
        )
        later = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 1),
            enddate=datetime(2025, 8, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=later, text="plus tard")
        ExhibitionText.objects.create(language=self.french, exhibition=later, text="Texte d'août.")

        out = StringIO()
        call_command("generate_english_texts", "--from", "2025-08-01", stdout=out)

        text = out.getvalue()
        self.assertIn("Looking for French texts to translate from 2025-08-01", text)
        self.assertIn("To translate: 1", text)
        self.assertIn("Texte d'août.", text)
        self.assertNotIn("Une salle blanche.", text)

    def test_rejects_an_invalid_from_date(self) -> None:
        with self.assertRaisesMessage(CommandError, "YYYY-MM-DD"):
            call_command("generate_english_texts", "--from", "20-03-2024")
