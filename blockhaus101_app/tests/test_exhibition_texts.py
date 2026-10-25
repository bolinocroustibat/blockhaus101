"""Tests for bilingual exhibition text creation."""

from datetime import datetime
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from blockhaus101_app.helpers.exhibition_text import create_exhibition_texts
from blockhaus101_app.models import Exhibition, ExhibitionText, ExhibitionTitle
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
    api.client.close = AsyncMock()
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

    def test_copies_a_plain_ip_from_the_french_text(self) -> None:
        french = ExhibitionText.objects.create(
            language=self.french,
            exhibition=self.exhibition,
            text="Une salle.",
            ip="1.2.3.4",
        )

        with patch(
            "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
            return_value=_openai_mock(),
        ):
            texts = create_exhibition_texts(self.exhibition, french=french)

        assert texts["en"] is not None
        self.assertEqual(texts["en"].ip, "1.2.3.4")

    def test_strips_a_cidr_suffix_from_the_copied_ip(self) -> None:
        french = ExhibitionText.objects.create(
            language=self.french,
            exhibition=self.exhibition,
            text="Une salle.",
            ip="1.2.3.4",
        )
        french.ip = "220.146.192.136/32                     "

        with patch(
            "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
            return_value=_openai_mock(),
        ):
            texts = create_exhibition_texts(self.exhibition, french=french)

        assert texts["en"] is not None
        self.assertEqual(texts["en"].ip, "220.146.192.136")


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

    def test_save_continues_after_one_show_fails(self) -> None:
        ExhibitionText.objects.create(
            language=self.french, exhibition=self.exhibition, text="Premier."
        )
        later = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 1),
            enddate=datetime(2025, 8, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=later, text="plus tard")
        ExhibitionTitle.objects.create(language=self.english, exhibition=later, text="later on")
        ExhibitionText.objects.create(language=self.french, exhibition=later, text="Deuxième.")

        calls = {"count": 0}

        def fail_then_ok(exhibition, french=None, ip=None):
            calls["count"] += 1
            if calls["count"] == 1:
                raise ValueError("bad ip")
            return create_exhibition_texts(exhibition, french=french, ip=ip)

        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.generate_english_texts.create_exhibition_texts",
                side_effect=fail_then_ok,
            ),
            patch(
                "blockhaus101_app.helpers.exhibition_text.OpenAiAPI",
                return_value=_openai_mock(),
            ),
        ):
            call_command("generate_english_texts", "--save", stdout=out)

        self.assertIn("Saved 1 English text(s). Failed: 1.", out.getvalue())
        self.assertEqual(ExhibitionText.objects.filter(language=self.english).count(), 1)


class TestReformulateExpoTextsCommand(ExhibitionTextFixture):
    def _french_text(self, exhibition: Exhibition, text: str) -> ExhibitionText:
        return ExhibitionText.objects.create(language=self.french, exhibition=exhibition, text=text)

    def test_rejects_an_invalid_from_date(self) -> None:
        with self.assertRaisesMessage(CommandError, "YYYY-MM-DD"):
            call_command("reformulate_expo_texts", "--from", "20-03-2024")

    def test_rejects_an_invalid_to_date(self) -> None:
        with self.assertRaisesMessage(CommandError, "YYYY-MM-DD"):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", "--to", "20-03-2024")

    def test_rejects_a_to_date_before_from(self) -> None:
        with self.assertRaisesMessage(CommandError, "--to must be on or after --from."):
            call_command("reformulate_expo_texts", "--from", "2025-08-01", "--to", "2025-03-01")

    def test_reports_when_no_french_text_matches(self) -> None:
        self._french_text(self.exhibition, "Une salle.")
        api = _openai_mock()
        out = StringIO()
        with patch(
            "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
            return_value=api,
        ):
            call_command("reformulate_expo_texts", "--from", "2026-01-01", stdout=out)

        self.assertIn("0 French text(s)", out.getvalue())
        api.reformulate.assert_not_called()

    def test_keeps_the_current_text_when_the_answer_is_no(self) -> None:
        french = self._french_text(self.exhibition, "Une salle.")
        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=_openai_mock(),
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", stdout=out)

        french.refresh_from_db()
        text = out.getvalue()
        self.assertIn("Une salle.", text)
        self.assertIn("Une salle blanche.", text)
        self.assertIn("Kept the current text.", text)
        self.assertIn("Replaced 0. Kept: 1. Failed: 0.", text)
        self.assertEqual(french.text, "Une salle.")
        self.assertIsNone(french.ai_model)

    def test_replaces_the_text_when_the_answer_is_yes(self) -> None:
        french = self._french_text(self.exhibition, "Une salle.")
        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=_openai_mock(),
            ),
            patch("builtins.input", return_value="y"),
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", stdout=out)

        french.refresh_from_db()
        self.assertIn("Replaced.", out.getvalue())
        self.assertEqual(french.text, "Une salle blanche.")
        self.assertEqual(french.ai_model, "gpt-test")

    def test_asks_once_per_text(self) -> None:
        first = self._french_text(self.exhibition, "Premier.")
        later = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 1),
            enddate=datetime(2025, 8, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=later, text="plus tard")
        second = self._french_text(later, "Deuxième.")

        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=_openai_mock(reformulated="Texte réécrit."),
            ),
            patch("builtins.input", side_effect=["n", "y"]),
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", stdout=out)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.text, "Premier.")
        self.assertEqual(second.text, "Texte réécrit.")
        self.assertEqual(second.ai_model, "gpt-test")
        self.assertIn("Replaced 1. Kept: 1. Failed: 0.", out.getvalue())

    def test_skips_confirmation_when_the_rewrite_fails(self) -> None:
        french = self._french_text(self.exhibition, "Une salle.")
        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=_openai_mock(reformulated=None, reformulate_error="unavailable"),
            ),
            patch("builtins.input") as prompt,
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", stdout=out)

        french.refresh_from_db()
        prompt.assert_not_called()
        self.assertIn("Rewrite failed: unavailable", out.getvalue())
        self.assertIn("Replaced 0. Kept: 0. Failed: 1.", out.getvalue())
        self.assertEqual(french.text, "Une salle.")

    def test_ignores_english_texts_and_older_shows(self) -> None:
        self._french_text(self.exhibition, "Une salle.")
        ExhibitionText.objects.create(
            language=self.english, exhibition=self.exhibition, text="A white room."
        )
        older = make_exhibition(
            self.artist,
            startdate=datetime(2024, 6, 1),
            enddate=datetime(2024, 6, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=older, text="avant")
        self._french_text(older, "Texte trop ancien.")

        api = _openai_mock()
        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=api,
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", stdout=out)

        self.assertEqual(api.reformulate.await_count, 1)
        self.assertEqual(api.reformulate.await_args.args, ())
        self.assertEqual(api.reformulate.await_args.kwargs["text"], "Une salle.")
        self.assertIn("1 French text(s)", out.getvalue())
        self.assertNotIn("Texte trop ancien.", out.getvalue())
        self.assertNotIn("A white room.", out.getvalue())

    def test_to_keeps_shows_through_the_end_of_that_day(self) -> None:
        self._french_text(self.exhibition, "Une salle.")
        on_the_day = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 1, 16, 52, 23),
            enddate=datetime(2025, 8, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=on_the_day, text="ce jour")
        self._french_text(on_the_day, "Texte du jour.")
        later = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 8),
            enddate=datetime(2025, 8, 15),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=later, text="après")
        self._french_text(later, "Texte trop tardif.")

        api = _openai_mock()
        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=api,
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command(
                "reformulate_expo_texts",
                "--from",
                "2025-03-01",
                "--to",
                "2025-08-01",
                stdout=out,
            )

        rewritten = [call.kwargs["text"] for call in api.reformulate.await_args_list]
        self.assertEqual(rewritten, ["Une salle.", "Texte du jour."])
        self.assertIn("through 2025-08-01", out.getvalue())
        self.assertNotIn("Texte trop tardif.", out.getvalue())

    def test_continues_after_a_request_crashes(self) -> None:
        first = self._french_text(self.exhibition, "Premier.")
        later = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 1),
            enddate=datetime(2025, 8, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=later, text="plus tard")
        second = self._french_text(later, "Deuxième.")
        api = _openai_mock(reformulated="Texte réécrit.")
        api.reformulate = AsyncMock(
            side_effect=[RuntimeError("Event loop is closed"), ("Texte réécrit.", 0.02, None)]
        )

        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=api,
            ) as api_cls,
            patch("builtins.input", return_value="y"),
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", stdout=out)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(api_cls.call_count, 2)
        self.assertEqual(api.client.close.await_count, 2)
        self.assertEqual(first.text, "Premier.")
        self.assertEqual(second.text, "Texte réécrit.")
        self.assertIn("Rewrite failed: Event loop is closed", out.getvalue())
        self.assertIn("Replaced 1. Kept: 0. Failed: 1.", out.getvalue())

    def test_yes_replaces_every_text_without_asking(self) -> None:
        first = self._french_text(self.exhibition, "Premier.")
        later = make_exhibition(
            self.artist,
            startdate=datetime(2025, 8, 1),
            enddate=datetime(2025, 8, 8),
        )
        ExhibitionTitle.objects.create(language=self.french, exhibition=later, text="plus tard")
        second = self._french_text(later, "Deuxième.")

        out = StringIO()
        with (
            patch(
                "blockhaus101_app.management.commands.reformulate_expo_texts.OpenAiAPI",
                return_value=_openai_mock(reformulated="Texte réécrit."),
            ),
            patch("builtins.input") as prompt,
        ):
            call_command("reformulate_expo_texts", "--from", "2025-01-01", "--yes", stdout=out)

        first.refresh_from_db()
        second.refresh_from_db()
        prompt.assert_not_called()
        self.assertEqual(first.text, "Texte réécrit.")
        self.assertEqual(second.text, "Texte réécrit.")
        self.assertEqual(first.ai_model, "gpt-test")
        self.assertIn("without asking", out.getvalue())
        self.assertIn("Replaced 2. Kept: 0. Failed: 0.", out.getvalue())
