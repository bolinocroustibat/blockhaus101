"""Checks for exhibitions that have no image or a missing image file."""

from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from blockhaus101_app.models import Exhibition
from blockhaus101_app.tests.factories import make_artist, make_exhibition


class TestCheckExhibitionImages(TestCase):
    def setUp(self) -> None:
        self.artist = make_artist()

    def _exhibition(self, start: datetime, *, image: str | None = None) -> Exhibition:
        exhibition = make_exhibition(
            self.artist,
            startdate=start,
            enddate=datetime(start.year, start.month, start.day, 18, 0, 0),
        )
        if image is not None:
            exhibition.image1 = image
            exhibition.save(update_fields=["image1"])
        return exhibition

    def test_counts_missing_links_and_missing_files(self) -> None:
        with TemporaryDirectory() as media, TemporaryDirectory() as static:
            media_folder = Path(media) / "exhibitions_imgs"
            static_folder = Path(static) / "exhibitions_imgs"
            media_folder.mkdir()
            static_folder.mkdir()
            (media_folder / "present.jpeg").write_bytes(b"img")
            (static_folder / "static-only.jpeg").write_bytes(b"img")
            self._exhibition(datetime(2024, 1, 1), image="exhibitions_imgs/present.jpeg")
            self._exhibition(datetime(2024, 1, 2), image="exhibitions_imgs/static-only.jpeg")
            self._exhibition(datetime(2024, 2, 1), image="exhibitions_imgs/gone.jpeg")
            self._exhibition(datetime(2024, 3, 1))

            out = StringIO()
            with override_settings(MEDIA_ROOT=media, STATIC_ROOT=static):
                call_command("check_exhibition_images", stdout=out)

        text = out.getvalue()
        self.assertIn("Exhibitions checked: 4", text)
        self.assertIn("No image attached: 1", text)
        self.assertIn("Image file missing: 1", text)
        self.assertIn("Image file present: 2", text)

    def test_from_limits_the_check_to_later_exhibitions(self) -> None:
        self._exhibition(datetime(2024, 1, 1))
        self._exhibition(datetime(2024, 6, 1))

        out = StringIO()
        call_command("check_exhibition_images", "--from", "2024-06-01", stdout=out)

        text = out.getvalue()
        self.assertIn("Checking exhibition images from 2024-06-01", text)
        self.assertIn("Exhibitions checked: 1", text)
        self.assertIn("No image attached: 1", text)

    def test_rejects_an_invalid_from_date(self) -> None:
        with self.assertRaisesMessage(CommandError, "YYYY-MM-DD"):
            call_command("check_exhibition_images", "--from", "20-03-2024")

    def test_generate_creates_images_only_after_confirmation(self) -> None:
        missing = self._exhibition(datetime(2024, 2, 1), image="exhibitions_imgs/gone.jpeg")
        untouched = self._exhibition(datetime(2024, 1, 1), image="exhibitions_imgs/present.jpeg")
        empty = self._exhibition(datetime(2024, 3, 1))
        generated_ids: list[int] = []

        def fake_generate(exhibition: Exhibition, img_format: str = "jpeg") -> ContentFile:
            generated_ids.append(exhibition.pk)
            return ContentFile(b"img", name="generated.jpeg")

        out = StringIO()
        with TemporaryDirectory() as media:
            present = Path(media) / "exhibitions_imgs"
            present.mkdir()
            (present / "present.jpeg").write_bytes(b"img")
            with (
                override_settings(MEDIA_ROOT=media, STATIC_ROOT=media),
                patch.object(Exhibition, "generate_image", fake_generate),
                patch.object(Exhibition, "save"),
                patch("builtins.input", return_value="y") as prompt,
            ):
                call_command("check_exhibition_images", "--generate", stdout=out)

        prompt.assert_called_once()
        self.assertCountEqual(generated_ids, [missing.pk, empty.pk])
        self.assertNotIn(untouched.pk, generated_ids)
        self.assertIn("Generated 2 image(s). Failed: 0.", out.getvalue())

    def test_generate_stops_when_declined(self) -> None:
        self._exhibition(datetime(2024, 3, 1))
        out = StringIO()
        with (
            patch.object(Exhibition, "generate_image") as generate,
            patch("builtins.input", return_value="n"),
        ):
            call_command("check_exhibition_images", "--generate", stdout=out)

        generate.assert_not_called()
        self.assertIn("Generation cancelled.", out.getvalue())

    def test_does_not_ask_to_generate_without_the_flag(self) -> None:
        self._exhibition(datetime(2024, 3, 1))
        with (
            patch.object(Exhibition, "generate_image") as generate,
            patch("builtins.input") as prompt,
        ):
            call_command("check_exhibition_images", stdout=StringIO())

        prompt.assert_not_called()
        generate.assert_not_called()

    def test_does_not_save_when_generation_returns_nothing(self) -> None:
        self._exhibition(datetime(2024, 3, 1))
        out = StringIO()
        with (
            patch.object(Exhibition, "generate_image", return_value=None),
            patch.object(Exhibition, "save") as save,
            patch("builtins.input", return_value="y"),
        ):
            call_command("check_exhibition_images", "--generate", stdout=out)

        save.assert_not_called()
        self.assertIn("Generated 0 image(s). Failed: 1.", out.getvalue())
