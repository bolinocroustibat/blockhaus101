"""Unit tests for OpenAI and GetImg.AI helpers. HTTP clients are mocked."""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import niquests
from django.test import SimpleTestCase
from openai import OpenAIError

from base_data_app.models.language import Language
from blockhaus101.image_model_pricing import (
    GETIMGAI_IMAGE_MODELS_PRICING,
    OPENAI_IMAGE_MODELS_PRICING,
)
from blockhaus101.settings import GETIMGAI_API_URL, GETIMGAI_IMAGE_MODEL, OPENAI_IMAGE_MODEL
from blockhaus101_app.helpers import GetImgAiAPI, OpenAiAPI


def _async_session(post_result: Any = None, post_error: Exception | None = None) -> MagicMock:
    """Build an AsyncSession stand-in whose client.post is awaitable."""
    client = AsyncMock()
    if post_error is not None:
        client.post = AsyncMock(side_effect=post_error)
    else:
        client.post = AsyncMock(return_value=post_result)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=client)
    session.__aexit__ = AsyncMock(return_value=False)
    session.client = client
    return session


class TestGetImgAiAPI(SimpleTestCase):
    def test_generate_image_returns_url_and_cost(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.text = json.dumps(
            {
                "data": [{"url": "https://cdn.example/image.jpg"}],
                "usage": {"total_cost": 0.14},
            }
        )
        session = _async_session(post_result=response)

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery", output_format="png"))

        self.assertEqual(result, {"url": "https://cdn.example/image.jpg", "cost": 0.14})
        session.client.post.assert_awaited_once()
        _args, kwargs = session.client.post.call_args
        self.assertEqual(_args[0], f"{GETIMGAI_API_URL}/v2/images/generations")
        self.assertEqual(
            kwargs["json"],
            {
                "model": GETIMGAI_IMAGE_MODEL["id"],
                "prompt": "a gallery",
                "aspect_ratio": GETIMGAI_IMAGE_MODEL["aspect_ratio"],
                "output_format": "png",
            },
        )

    def test_generate_image_returns_none_when_request_fails(self) -> None:
        session = _async_session(post_error=niquests.RequestException("network down"))

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery"))

        self.assertIsNone(result)

    def test_generate_image_returns_none_on_timeout(self) -> None:
        session = _async_session(post_error=TimeoutError())

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery"))

        self.assertIsNone(result)

    def test_generate_image_returns_none_on_empty_body(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.text = None
        session = _async_session(post_result=response)

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery"))

        self.assertIsNone(result)

    def test_generate_image_returns_none_on_invalid_json(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.text = "not-json"
        session = _async_session(post_result=response)

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery"))

        self.assertIsNone(result)

    def test_generate_image_returns_none_on_api_error(self) -> None:
        response = MagicMock()
        response.status_code = 400
        response.text = json.dumps({"error": {"message": "Unsupported resolution"}})
        session = _async_session(post_result=response)

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery"))

        self.assertIsNone(result)

    def test_generate_image_returns_none_when_url_is_missing(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.text = json.dumps({"data": [{}], "usage": {"total_cost": 0.1}})
        session = _async_session(post_result=response)

        with patch(
            "blockhaus101_app.helpers.api_getimgai.niquests.AsyncSession",
            return_value=session,
        ):
            result = asyncio.run(GetImgAiAPI().generate_image("a gallery"))

        self.assertIsNone(result)


class TestOpenAiAPI(SimpleTestCase):
    def setUp(self) -> None:
        # The client rejects an empty key before any request. These tests replace it.
        patcher = patch("blockhaus101_app.helpers.api_openai.AsyncOpenAI")
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_generate_image_returns_b64_data(self) -> None:
        api = OpenAiAPI()
        image = MagicMock()
        image.b64_json = "abc123"
        response = MagicMock()
        response.data = [image]
        api.client = MagicMock()
        api.client.images.generate = AsyncMock(return_value=response)

        b64_data, price, error_msg = asyncio.run(
            api.generate_image("a gallery", output_format="png")
        )

        self.assertEqual(b64_data, "abc123")
        self.assertIsNone(price)
        self.assertIsNone(error_msg)
        api.client.images.generate.assert_awaited_once_with(
            model=OPENAI_IMAGE_MODEL["id"],
            prompt="a gallery",
            size=OPENAI_IMAGE_MODEL["size"],
            quality=OPENAI_IMAGE_MODEL["quality"],
            output_format="png",
        )

    def test_generate_image_returns_error_on_openai_failure(self) -> None:
        api = OpenAiAPI()
        api.client = MagicMock()
        api.client.images.generate = AsyncMock(side_effect=OpenAIError("unavailable"))

        b64_data, price, error_msg = asyncio.run(api.generate_image("a gallery"))

        self.assertIsNone(b64_data)
        self.assertIsNone(price)
        self.assertIsNotNone(error_msg)
        self.assertIn("unavailable", error_msg or "")

    def test_generate_image_returns_error_when_image_is_missing(self) -> None:
        api = OpenAiAPI()
        response = MagicMock()
        response.data = []
        api.client = MagicMock()
        api.client.images.generate = AsyncMock(return_value=response)

        b64_data, price, error_msg = asyncio.run(api.generate_image("a gallery"))

        self.assertIsNone(b64_data)
        self.assertIsNone(price)
        self.assertEqual(error_msg, "OpenAI image request returned no image data")

    def test_get_models_ids_returns_ids(self) -> None:
        api = OpenAiAPI()
        model = MagicMock()
        model.id = "gpt-4o-mini"
        listed = MagicMock()
        listed.data = [model]
        api.client = MagicMock()
        api.client.models.list = AsyncMock(return_value=listed)

        self.assertEqual(asyncio.run(api.get_models_ids()), ["gpt-4o-mini"])

    def test_get_models_ids_returns_empty_list_on_error(self) -> None:
        api = OpenAiAPI()
        api.client = MagicMock()
        api.client.models.list = AsyncMock(side_effect=OpenAIError("unavailable"))

        self.assertEqual(asyncio.run(api.get_models_ids()), [])

    def test_translate_returns_processed_text(self) -> None:
        api = OpenAiAPI()
        api._process_openai_request = AsyncMock(return_value=("Hello", 0.001, None))  # type: ignore[method-assign]
        origin = Language(code="fr", name="French")
        dest = Language(code="en", name="English")

        text, price, error_msg = asyncio.run(api.translate("Bonjour", origin, dest))

        self.assertEqual(text, "Hello")
        self.assertEqual(price, 0.001)
        self.assertIsNone(error_msg)
        await_args = api._process_openai_request.await_args
        self.assertIsNotNone(await_args)
        assert await_args is not None
        messages = await_args.args[0]
        self.assertIn("French", messages[0]["content"])
        self.assertIn("English", messages[0]["content"])
        self.assertIn("deadpan", messages[0]["content"])
        self.assertEqual(messages[1]["content"], "Bonjour")

    def test_text_request_uses_a_low_temperature(self) -> None:
        api = OpenAiAPI()
        choice = MagicMock()
        choice.finish_reason = "stop"
        choice.message.content = "Hello"
        usage = MagicMock()
        usage.total_tokens = 10
        usage.prompt_tokens = 8
        usage.completion_tokens = 2
        response = MagicMock()
        response.choices = [choice]
        response.usage = usage
        api.client = MagicMock()
        api.client.chat.completions.create = AsyncMock(return_value=response)
        origin = Language(code="fr", name="French")
        dest = Language(code="en", name="English")

        asyncio.run(api.translate("Bonjour", origin, dest))

        await_args = api.client.chat.completions.create.await_args
        self.assertIsNotNone(await_args)
        assert await_args is not None
        self.assertEqual(await_args.kwargs["temperature"], 0.2)
        self.assertEqual(await_args.kwargs["model"], api.model["id"])

    def test_reformulate_strips_guillemets(self) -> None:
        api = OpenAiAPI()
        api._process_openai_request = AsyncMock(  # type: ignore[method-assign]
            return_value=("« Un texte allongé »", 0.002, None)
        )

        text, price, error_msg = asyncio.run(api.reformulate("Un texte"))

        self.assertEqual(text, "Un texte allongé")
        self.assertEqual(price, 0.002)
        self.assertIsNone(error_msg)
        await_args = api._process_openai_request.await_args
        self.assertIsNotNone(await_args)
        assert await_args is not None
        messages = await_args.args[0]
        self.assertIn("jamais plus court", messages[0]["content"])
        self.assertEqual(messages[1]["content"], "Un texte")

    def test_calculate_request_price(self) -> None:
        api = OpenAiAPI()
        # 1M input + 1M output tokens at the configured rates
        self.assertAlmostEqual(api.calculate_request_price(1_000_000, 1_000_000), 0.75)


class ImageModelPricingCatalogTests(SimpleTestCase):
    def test_active_models_have_catalog_pricing(self) -> None:
        openai_id = OPENAI_IMAGE_MODEL["id"]
        getimg_id = GETIMGAI_IMAGE_MODEL["id"]
        self.assertIn(openai_id, OPENAI_IMAGE_MODELS_PRICING)
        self.assertIn(getimg_id, GETIMGAI_IMAGE_MODELS_PRICING)
        self.assertEqual(OPENAI_IMAGE_MODEL["pricing"], OPENAI_IMAGE_MODELS_PRICING[openai_id])
        self.assertEqual(GETIMGAI_IMAGE_MODEL["pricing"], GETIMGAI_IMAGE_MODELS_PRICING[getimg_id])
