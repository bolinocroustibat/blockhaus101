import asyncio
from datetime import datetime, timedelta
from typing import Any, Literal

from django.core.management.base import BaseCommand, CommandError

from blockhaus101.settings import logger
from blockhaus101_app.helpers import OpenAiAPI
from blockhaus101_app.models import ExhibitionText

Outcome = Literal["replaced", "kept", "failed"]


class Command(BaseCommand):
    help = (
        "Rewrite French exhibition texts between two start dates. "
        "Shows each rewritten text and asks before replacing it, unless --yes is set."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--from",
            dest="from_date",
            required=True,
            metavar="YYYY-MM-DD",
            help="Only exhibitions starting on or after this date",
        )
        parser.add_argument(
            "--to",
            dest="to_date",
            default=None,
            metavar="YYYY-MM-DD",
            help="Only exhibitions starting on or before this date",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Replace every rewritten text without asking",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from_date = self._parse_date(options["from_date"])
        to_date = self._parse_date(options["to_date"]) if options["to_date"] else None
        if to_date is not None and to_date < from_date:
            raise CommandError("--to must be on or after --from.")

        texts = ExhibitionText.objects.filter(
            language__code="fr",
            exhibition__startdate__gte=from_date,
        )
        if to_date is not None:
            texts = texts.filter(exhibition__startdate__lt=to_date + timedelta(days=1))
        texts = list(
            texts.select_related("exhibition", "exhibition__artist").order_by(
                "exhibition__startdate", "exhibition__pk", "pk"
            )
        )
        if to_date is not None:
            period = f"from {from_date.date()} through {to_date.date()}"
        else:
            period = f"on or after {from_date.date()}"
        self.stdout.write(f"{len(texts)} French text(s) for exhibitions starting {period}.")
        if options["yes"]:
            self.stdout.write("Replacing each rewritten text without asking.")
        if not texts:
            return

        replaced = 0
        kept = 0
        failed = 0
        for index, exhibition_text in enumerate(texts, start=1):
            outcome = self._rewrite_one(
                index, len(texts), exhibition_text, assume_yes=options["yes"]
            )
            if outcome == "replaced":
                replaced += 1
            elif outcome == "kept":
                kept += 1
            else:
                failed += 1

        self.stdout.write(f"Replaced {replaced}. Kept: {kept}. Failed: {failed}.")

    def _rewrite_one(
        self,
        index: int,
        total: int,
        exhibition_text: ExhibitionText,
        *,
        assume_yes: bool,
    ) -> Outcome:
        exhibition = exhibition_text.exhibition
        start = exhibition.startdate.date() if exhibition.startdate else "no date"
        self.stdout.write("")
        self.stdout.write(
            f"[{index}/{total}] Exhibition {exhibition.pk} — {start} — {exhibition.artist.name}"
        )
        self.stdout.write(str(exhibition))
        self.stdout.write("Current text:")
        self.stdout.write(exhibition_text.text or "")

        try:
            reformulated_text, price, error_msg, model_id = asyncio.run(
                self._reformulate(exhibition_text.text or "")
            )
        except Exception as exc:  # noqa: BLE001 — one failure must not stop the batch
            logger.exception("Could not rewrite exhibition text %s", exhibition_text.pk)
            self.stdout.write(self.style.ERROR(f"Rewrite failed: {exc}"))
            return "failed"
        if error_msg or not reformulated_text:
            logger.error(
                "Could not rewrite exhibition text %s: %s",
                exhibition_text.pk,
                error_msg or "empty response",
            )
            self.stdout.write(self.style.ERROR(f"Rewrite failed: {error_msg or 'empty response'}"))
            return "failed"

        price_label = f"${price:.6f}" if price is not None else "unknown price"
        self.stdout.write(f"Rewritten text ({model_id}, {price_label}):")
        self.stdout.write(reformulated_text)

        if not assume_yes:
            confirm = input("\nReplace the current text? [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write("Kept the current text.")
                return "kept"

        exhibition_text.text = reformulated_text
        exhibition_text.ai_model = model_id
        exhibition_text.save()
        self.stdout.write(self.style.SUCCESS("Replaced."))
        return "replaced"

    async def _reformulate(self, text: str) -> tuple[str | None, float | None, str | None, str]:
        """Call OpenAI on a fresh client, then close it before the event loop ends.

        Reusing one client across ``asyncio.run()`` calls leaves its HTTP connection
        bound to a closed loop, and the next request crashes while closing that connection.
        """
        api = OpenAiAPI()
        try:
            result_text, price, error_msg = await api.reformulate(text=text)
            return result_text, price, error_msg, api.model["id"]
        finally:
            try:
                await api.client.close()
            except Exception:  # noqa: BLE001 — closing must not hide a finished rewrite
                logger.exception("Could not close the OpenAI client")

    def _parse_date(self, value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise CommandError(
                "Invalid date format. Please use YYYY-MM-DD (e.g. 2024-03-20)."
            ) from exc
