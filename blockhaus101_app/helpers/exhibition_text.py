from __future__ import annotations

import asyncio
import ipaddress

from base_data_app.models import Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers.api_openai import OpenAiAPI
from blockhaus101_app.models.exhibition import Exhibition
from blockhaus101_app.models.exhibition_text import ExhibitionText


def create_exhibition_texts(
    exhibition: Exhibition,
    *,
    french: ExhibitionText | None = None,
    ip: str | None = None,
) -> dict[str, ExhibitionText | None]:
    """Save a French exhibition text and an English translation of it.

    When ``french`` is omitted, generate and reformulate a new French text.
    When an English text already exists, it is returned and OpenAI is not called.
    A failed translation still leaves the French text saved.
    """
    if french is None:
        french = _generate_french_text(exhibition, ip=ip)
    if french.pk is None:
        french.save()

    existing_english = ExhibitionText.objects.filter(
        exhibition=exhibition, language__code="en"
    ).last()
    if existing_english:
        return {"fr": french, "en": existing_english}

    return {"fr": french, "en": _save_english_translation(french, ip=ip)}


def _generate_french_text(exhibition: Exhibition, *, ip: str | None) -> ExhibitionText:
    french_language = Language.objects.get(code="fr")
    french = ExhibitionText(language=french_language, exhibition=exhibition, ip=ip)
    french.generate()
    openai_api = OpenAiAPI()
    reformulated_text, price, error_msg = asyncio.run(
        openai_api.reformulate(text=str(french.text), language=french_language)
    )
    if reformulated_text:
        logger.info(
            f"Text has been reformulated by OpenAI {openai_api.model['id']}:"
            f"\n{reformulated_text}\nCost: {price}$"
        )
        french = ExhibitionText(
            language=french_language,
            exhibition=exhibition,
            ip=ip,
            text=reformulated_text,
            ai_model=openai_api.model["id"],
        )
    if error_msg:
        logger.error(f"Error while reformulating text: {error_msg}")
    return french


def _save_english_translation(french: ExhibitionText, *, ip: str | None) -> ExhibitionText | None:
    english_language = Language.objects.get(code="en")
    openai_api = OpenAiAPI()
    translated, price, error_msg = asyncio.run(
        openai_api.translate(
            text=str(french.text),
            origin_language=french.language,
            dest_language=english_language,
        )
    )
    if error_msg:
        logger.error(f"Error while translating exhibition text: {error_msg}")
    if not translated:
        return None

    logger.info(
        f"Text has been translated by OpenAI {openai_api.model['id']}:"
        f"\n{translated}\nCost: {price}$"
    )
    english = ExhibitionText(
        language=english_language,
        exhibition=french.exhibition,
        ip=usable_ip(ip if ip is not None else french.ip),
        text=translated,
        ai_model=openai_api.model["id"],
    )
    english.save()
    return english


def usable_ip(value: str | None) -> str | None:
    """Return a plain IPv4/IPv6 address, or None when the value cannot be stored."""
    if not value:
        return None
    cleaned = value.strip().split("/", 1)[0].strip()
    if not cleaned:
        return None
    try:
        ipaddress.ip_address(cleaned)
    except ValueError:
        return None
    return cleaned
