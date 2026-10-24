"""Report exhibitions with no image or a missing image file."""

from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet

from blockhaus101.settings import logger
from blockhaus101_app.models import Exhibition


def image_filename(exhibition: Exhibition) -> str:
    """Return the stored image filename, or an empty string when there is none."""
    image = exhibition.image1
    name = image.name if image else ""
    if not name:
        return ""
    return Path(name).name


def image_file_exists(exhibition: Exhibition) -> bool:
    """Return whether the linked exhibition image is present on disk."""
    image = exhibition.image1
    name = image.name if image else ""
    if not name:
        return False

    filename = Path(name).name
    candidates = {
        Path(settings.MEDIA_ROOT) / name,
        Path(settings.MEDIA_ROOT) / "exhibitions_imgs" / filename,
        Path(settings.STATIC_ROOT) / "exhibitions_imgs" / filename,
    }
    return any(path.is_file() for path in candidates)


class Command(BaseCommand):
    help = (
        "Report exhibitions with no image or a missing image file. "
        "Pass --generate to be asked to create those images."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show each exhibition",
        )
        parser.add_argument(
            "--from",
            dest="from_date",
            metavar="YYYY-MM-DD",
            help="Only exhibitions starting on or after this date",
        )
        parser.add_argument(
            "--generate",
            action="store_true",
            help="Ask to generate images for exhibitions with no image or a missing file",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from_date = self._parse_from_date(options.get("from_date"))
        exhibitions = list(self._exhibitions(from_date))
        no_image, missing_file, present = self._classify(exhibitions)
        self._report(exhibitions, no_image, missing_file, present, from_date, options["verbose"])

        if no_image or missing_file:
            logger.warning(
                "Exhibition images: %s with no image, %s with a missing file, out of %s checked",
                len(no_image),
                len(missing_file),
                len(exhibitions),
            )
        else:
            logger.info("All checked exhibitions have an image file")

        if options["generate"]:
            self._generate(no_image, missing_file)

    def _parse_from_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise CommandError(
                "Invalid date format. Please use YYYY-MM-DD (e.g. 2024-03-20)."
            ) from exc

    def _exhibitions(self, from_date: datetime | None) -> QuerySet[Exhibition]:
        exhibitions = Exhibition.objects.all().order_by("startdate", "pk")
        if from_date is not None:
            return exhibitions.filter(startdate__gte=from_date)
        return exhibitions

    def _classify(
        self, exhibitions: list[Exhibition]
    ) -> tuple[list[Exhibition], list[Exhibition], list[Exhibition]]:
        no_image: list[Exhibition] = []
        missing_file: list[Exhibition] = []
        present: list[Exhibition] = []
        for exhibition in exhibitions:
            if not exhibition.image1:
                no_image.append(exhibition)
            elif image_file_exists(exhibition):
                present.append(exhibition)
            else:
                missing_file.append(exhibition)
        return no_image, missing_file, present

    def _report(
        self,
        exhibitions: list[Exhibition],
        no_image: list[Exhibition],
        missing_file: list[Exhibition],
        present: list[Exhibition],
        from_date: datetime | None,
        verbose: bool,
    ) -> None:
        scope = f" from {from_date.date().isoformat()}" if from_date else ""
        self.stdout.write(f"Checking exhibition images{scope}...")
        self.stdout.write("=" * 50)

        if verbose:
            for exhibition in no_image:
                self.stdout.write(f"  no image: {exhibition.pk}: {exhibition}")
            for exhibition in missing_file:
                self.stdout.write(
                    f"  missing file: {exhibition.pk}: {exhibition} - {image_filename(exhibition)}"
                )
            for exhibition in present:
                self.stdout.write(
                    f"  ok: {exhibition.pk}: {exhibition} - {image_filename(exhibition)}"
                )

        self.stdout.write("\nSummary:")
        self.stdout.write(f"  Exhibitions checked: {len(exhibitions)}")
        self.stdout.write(f"  No image attached: {len(no_image)}")
        self.stdout.write(f"  Image file missing: {len(missing_file)}")
        self.stdout.write(f"  Image file present: {len(present)}")

    def _generate(self, no_image: list[Exhibition], missing_file: list[Exhibition]) -> None:
        to_generate = no_image + missing_file
        if not to_generate:
            self.stdout.write("Nothing to generate.")
            return

        confirm = input(
            f"\nGenerate images for {len(to_generate)} exhibition(s) "
            f"({len(no_image)} with no image, {len(missing_file)} with a missing file)? [y/N]: "
        )
        if confirm.lower() != "y":
            self.stdout.write("Generation cancelled.")
            return

        generated = 0
        failed = 0
        for exhibition in to_generate:
            self.stdout.write(f"Generating image for exhibition {exhibition.pk}...")
            try:
                content = exhibition.generate_image()
            except Exception as exc:  # noqa: BLE001 — one failure must not stop the batch
                logger.error("Image generation failed for exhibition %s: %s", exhibition.pk, exc)
                failed += 1
                continue
            if content is None:
                logger.error("Image generation returned nothing for exhibition %s", exhibition.pk)
                failed += 1
                continue
            exhibition.save()
            generated += 1
            logger.info("Image generated and saved for exhibition %s", exhibition.pk)

        self.stdout.write(f"Generated {generated} image(s). Failed: {failed}.")
