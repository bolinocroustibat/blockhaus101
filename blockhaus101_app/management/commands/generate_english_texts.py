from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from blockhaus101.settings import logger
from blockhaus101_app.helpers.exhibition_text import create_exhibition_texts
from blockhaus101_app.models import Exhibition, ExhibitionText


class Command(BaseCommand):
    help = (
        "Translate French exhibition texts into English. "
        "Without --save, print the shows that would be translated."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--from",
            dest="from_date",
            metavar="YYYY-MM-DD",
            default="2025-01-01",
            help="Only exhibitions starting on or after this date (default: 2025-01-01)",
        )
        parser.add_argument(
            "--save",
            action="store_true",
            help="Translate and save English texts",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from_date = self._parse_from_date(options["from_date"])
        to_translate, skipped_no_french, skipped_has_english = self._pending(from_date)

        self.stdout.write(f"Looking for French texts to translate from {from_date.date()}")
        self.stdout.write(f"To translate: {len(to_translate)}")
        self.stdout.write(f"Skipped, no French text: {skipped_no_french}")
        self.stdout.write(f"Skipped, English already present: {skipped_has_english}")
        for exhibition, french in to_translate:
            self.stdout.write(f"  {exhibition.pk} {exhibition} — {french.text[:60]}")

        if not options["save"]:
            self.stdout.write("Dry run. Pass --save to translate and write English texts.")
            return

        saved = 0
        failed = 0
        for exhibition, french in to_translate:
            try:
                texts = create_exhibition_texts(exhibition, french=french)
            except (ValueError, ValidationError, DatabaseError) as error:
                failed += 1
                logger.error(f"Could not translate exhibition {exhibition.pk}: {error}")
                continue
            if texts.get("en"):
                saved += 1
            else:
                failed += 1
                logger.error(f"Could not translate exhibition {exhibition.pk}")

        self.stdout.write(f"Saved {saved} English text(s). Failed: {failed}.")

    def _parse_from_date(self, value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise CommandError(
                "Invalid date format. Please use YYYY-MM-DD (e.g. 2024-03-20)."
            ) from exc

    def _pending(
        self, from_date: datetime
    ) -> tuple[list[tuple[Exhibition, ExhibitionText]], int, int]:
        exhibitions = Exhibition.objects.filter(startdate__gte=from_date).order_by(
            "startdate", "pk"
        )
        to_translate: list[tuple[Exhibition, ExhibitionText]] = []
        skipped_no_french = 0
        skipped_has_english = 0
        for exhibition in exhibitions:
            french = ExhibitionText.objects.filter(
                exhibition=exhibition, language__code="fr"
            ).last()
            if french is None:
                skipped_no_french += 1
                continue
            if ExhibitionText.objects.filter(exhibition=exhibition, language__code="en").exists():
                skipped_has_english += 1
                continue
            to_translate.append((exhibition, french))
        return to_translate, skipped_no_french, skipped_has_english
