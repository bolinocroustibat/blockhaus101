import asyncio

from django.core.management.base import BaseCommand

from blockhaus101.settings import logger
from blockhaus101_app.helpers import OpenAiAPI


class Command(BaseCommand):
    help = "Get IDs of available OpenAI models"

    def handle(self, *args, **options):
        openai_api = OpenAiAPI()
        models: list[str] = asyncio.run(openai_api.get_models_ids())
        logger.info(f"IDs of available OpenAI models:\n- {"\n- ".join(models)}")
