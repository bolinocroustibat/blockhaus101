from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from blockhaus101_app.models.artist import Artist
from blockhaus101_app.models.artist_bio import ArtistBiography
from blockhaus101_app.models.exhibition import Exhibition
from blockhaus101_app.models.exhibition_text import ExhibitionText
from blockhaus101_app.models.exhibition_title import ExhibitionTitle


class Command(BaseCommand):
    help = "Delete all exhibitions and related data after a specific date"

    def add_arguments(self, parser):
        parser.add_argument(
            "date",
            type=str,
            help="Date in YYYY-MM-DD format after which to delete exhibitions (e.g., 2024-03-20)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            # Parse the input date
            cutoff_date = datetime.strptime(options["date"], "%Y-%m-%d").date()

            # Get exhibitions after the cutoff date
            exhibitions = Exhibition.objects.filter(startdate__gte=cutoff_date)

            if not exhibitions.exists():
                self.stdout.write(self.style.WARNING(f"No exhibitions found after {cutoff_date}"))
                return

            # Count related objects for confirmation
            exhibition_count = exhibitions.count()
            titles = ExhibitionTitle.objects.filter(exhibition__in=exhibitions)
            texts = ExhibitionText.objects.filter(exhibition__in=exhibitions)
            artists = Artist.objects.filter(exhibitions__in=exhibitions)
            bios = ArtistBiography.objects.filter(artist__in=artists)

            # Show summary of what will be deleted
            self.stdout.write(
                self.style.WARNING(
                    f"\nThe following will be deleted:\n"
                    f"- {exhibition_count} exhibitions\n"
                    f"- {titles.count()} exhibition titles\n"
                    f"- {texts.count()} exhibition texts\n"
                    f"- {artists.count()} artists\n"
                    f"- {bios.count()} artist biographies\n"
                )
            )

            # Ask for confirmation
            confirm = input("\nAre you sure you want to proceed? [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Operation cancelled"))
                return

            # Delete everything in a transaction
            with transaction.atomic():
                # Delete in reverse order of dependencies
                bios.delete()
                artists.delete()
                texts.delete()
                titles.delete()
                exhibitions.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {exhibition_count} exhibitions and related data"
                )
            )

        except ValueError:
            raise CommandError(
                "Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-03-20)"
            )
        except Exception as e:
            raise CommandError(f"An error occurred: {e!s}")
