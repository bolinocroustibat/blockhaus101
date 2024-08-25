import csv
import re

import httpx
from django.core.management.base import BaseCommand

from base_data_app.models import Data, DataType, Language
from blockhaus101.settings import logger


class Command(BaseCommand):
    help = "Import data from Google Sheet"

    def handle(self, *args, **options):
        csv_url = (
            input(
                "Enter the Google Sheet tab CSV URL (example: https://docs.google.com/spreadsheets/d/e/2PACX-1vQsf4u3bXTdNL-nkiRuBpnndfZJXyowxIBtXK9vbLodtJuO3s3XQmMTr78x-jodpOK6_LUJvse1fv-U/pub?gid=1997643286&single=true&output=csv): "
            )
            or "https://docs.google.com/spreadsheets/d/e/2PACX-1vQsf4u3bXTdNL-nkiRuBpnndfZJXyowxIBtXK9vbLodtJuO3s3XQmMTr78x-jodpOK6_LUJvse1fv-U/pub?gid=1997643286&single=true&output=csv"
        )
        input_type = input("Enter name of the type for that tab: ")
        lang = input("Enter the language code for that tab ('fr' or 'en'): ") or "fr"
        skipped_rows = int(
            input("Enter the number of rows to skip at the beginning of the CSV (default: 3): ")
            or 3
        )
        language = Language.objects.get(lang=lang)
        response = httpx.get(url=csv_url)
        csv_bytestream = response.content.decode("utf-8")
        csv_reader = csv.reader(csv_bytestream.splitlines())
        for r in range(skipped_rows):
            next(csv_reader)
        line_count = 0
        data_type = DataType.objects.get_or_create(name=input_type, language=language)[0]
        data_to_be_deleted = Data.objects.filter(data_type=data_type)
        data_to_be_deleted.delete()
        for row in csv_reader:
            logger.debug(row)
            if len(row) == 1:
                logger.info("Tab has one column")
                Data.objects.create(data_type=data_type, text=row[0])
            elif len(row) == 2:
                logger.info("Tab has two columns, assuming the first is data, second one is gender")
                Data.objects.create(data_type=data_type, text=row[0], gender=row[1])
            else:
                logger.info(
                    "Tab has many columns, assuming it's a data structure, joining with spaces"
                )
                data = " ".join(row)
                keywords: list = re.findall(
                    r"\b(?<!\[)[A-Z-+]{2,}\b", data
                )  # find all uppercase words that are at least 2 characters long, and that have no bracket before them
                for k in set(keywords):
                    data = data.replace(k, f"[{k}]")
                data = self._normalize_text(text=data)
                Data.objects.create(data_type=data_type, text=data)
            line_count += 1
        logger.info(f"Processed {line_count} lines.")

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace(" ,", ",")
        text = text.replace(" .", ".")
        text = text.replace("“ ", '"')
        text = text.replace(" ”", '"')
        text = text.replace("( ", "(")
        text = text.replace(" )", ")")
        return text
