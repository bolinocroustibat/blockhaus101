import asyncio
import json

import niquests

from blockhaus101.settings import GETIMGAI_API_KEY, GETIMGAI_API_URL, GETIMGAI_IMAGE_MODEL, logger

GETIMGAI_TIMEOUT = 120


class GetImgAiAPI:
    def __init__(self) -> None:
        self.api_key = GETIMGAI_API_KEY
        self.base_url = GETIMGAI_API_URL
        self.model = GETIMGAI_IMAGE_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def generate_image(self, prompt: str, output_format: str = "jpeg") -> dict | None:
        """Generate an image using GetImg.AI v2.

        Returns a dict with `url` (signed download URL) and `cost`, or None on failure.
        """
        data = {
            "model": self.model["id"],
            "prompt": prompt,
            "aspect_ratio": self.model["aspect_ratio"],
            "output_format": output_format,
        }
        logger.debug(
            f"Sending GetImg v2 request with model={data['model']}, "
            f"aspect_ratio={data['aspect_ratio']}"
        )

        try:
            async with asyncio.timeout(GETIMGAI_TIMEOUT):
                async with niquests.AsyncSession() as client:
                    response = await client.post(
                        f"{self.base_url}/v2/images/generations",
                        headers=self.headers,
                        json=data,
                    )
        except (niquests.RequestException, TimeoutError) as e:
            logger.error(f"GetImg image request failed: {e!s}")
            return None

        if response is None or response.text is None:
            logger.error("Empty response from GetImg API")
            return None

        try:
            body = json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GetImg JSON response: {e!s}")
            return None

        if response.status_code != 200:
            error = body.get("error", {})
            message = error.get("message") if isinstance(error, dict) else body
            logger.error(f"GetImg API error: {message}")
            return None

        data_items = body.get("data") or []
        if not data_items or not data_items[0].get("url"):
            logger.error("GetImg API returned no image URL")
            return None

        cost = None
        usage = body.get("usage")
        if isinstance(usage, dict):
            cost = usage.get("total_cost")

        return {"url": data_items[0]["url"], "cost": cost}
