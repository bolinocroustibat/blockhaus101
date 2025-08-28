#!/usr/bin/env python
from pathlib import Path

from django.core.management.base import BaseCommand

from blockhaus101.settings import logger
from blockhaus101_app.models import Exhibition


class Command(BaseCommand):
    help = "Check which exhibition images are missing from the filesystem"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed information about each image",
        )

    def handle(self, *args, **options):
        print("Checking exhibition images...")
        print("=" * 50)

        total_with_images = 0
        found_in_container = 0
        missing_from_container = 0
        verbose = options.get("verbose", False)

        for ex in Exhibition.objects.filter(image1__isnull=False).exclude(image1=""):
            total_with_images += 1
            filename = Path(str(ex.image1)).name
            static_path = Path("/app/static/exhibitions_imgs") / filename
            media_path = Path("/app/media/exhibitions_imgs") / filename

            # Check if file exists in container
            if Path(static_path).exists or Path(media_path).exists:
                found_in_container += 1
                if verbose:
                    print(f"  ✓ {ex.id}: {ex} - {filename}")
            else:
                missing_from_container += 1
                if verbose:
                    print(f"  ✗ {ex.id}: {ex} - {filename}")

        print("\nSummary:")
        print(f"  Total exhibitions with image1: {total_with_images}")
        print(f"  Found in container: {found_in_container}")
        print(f"  Missing from container: {missing_from_container}")

        if missing_from_container > 0:
            print(
                f"\nNote: {missing_from_container} images are missing from the container filesystem."
            )
            print("This may be normal if your web server serves files from a different location.")
            print("Check if images are accessible via web URLs before regenerating.")
            logger.warning(
                f"Found {missing_from_container} images missing from container out of {total_with_images} total"
            )
        else:
            logger.info("All exhibition images are present in container")
