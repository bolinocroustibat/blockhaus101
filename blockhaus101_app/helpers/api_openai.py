from typing import Literal

from openai import AsyncOpenAI, OpenAIError

from base_data_app.models.language import Language
from blockhaus101.settings import (
    OPENAI_API_KEY,
    OPENAI_IMAGE_MODEL,
    OPENAI_MODEL,
    logger,
)


class OpenAiAPI:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.image_model = OPENAI_IMAGE_MODEL

    async def get_models_ids(self) -> list[str]:
        """Get the list of the official names for all the available OpenAI models."""
        try:
            models = await self.client.models.list()
            return [m.id for m in models.data]
        except OpenAIError as e:
            logger.error(f"Unable to get the list of OpenAI models: {e!s}")
            return []

    async def _process_openai_request(
        self, messages: list[dict]
    ) -> tuple[str | None, float | None, str | None]:
        """Common method to process OpenAI requests for both translation and reformulation.

        Args:
            messages (list[dict]): The messages to send to OpenAI
            operation (str): The type of operation being performed (for logging)

        Returns:
            tuple[str | None, float | None, str | None]: Processed text, price, and error message
        """
        result_text: str | None = None
        price: float | None = None
        error_msg: str | None = None

        logger.info("Requesting OpenAI...")
        try:
            response = await self.client.chat.completions.create(
                model=self.model["id"],
                messages=messages,  # type: ignore
                user="blockhaus101",
            )
        except OpenAIError as e:
            error_msg = f"Erreur lors de la requête OpenAI : {e!s}"
            logger.error(error_msg)
            return result_text, price, error_msg

        if response.choices[0].finish_reason == "length":
            error_msg = "Le texte est trop long pour ce modèle, veuillez utiliser un autre modèle dans les réglages."
            logger.error(error_msg)
            return result_text, price, error_msg

        try:
            tokens_usage: int = response.usage.total_tokens
            price = self.calculate_request_price(
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            logger.info(f"\nTokens used: {tokens_usage}. OpenAI request price: ${price:.6f}")
        except (AttributeError, KeyError, TypeError) as e:
            logger.error(f"\nUnable to calculate the price of the request: {e!s}")

        result_text = response.choices[0].message.content
        return result_text, price, error_msg

    async def generate_image(
        self, prompt: str, output_format: Literal["png", "jpeg", "webp"] = "jpeg"
    ) -> tuple[str | None, float | None, str | None]:
        """Generate an image from a text prompt using OpenAI Images."""
        b64_data: str | None = None
        price: float | None = None
        error_msg: str | None = None

        logger.info("Requesting OpenAI image generation...")
        try:
            response = await self.client.images.generate(
                model=self.image_model["id"],
                prompt=prompt,
                size=self.image_model["size"],
                quality=self.image_model["quality"],
                output_format=output_format,
            )
        except OpenAIError as e:
            error_msg = f"Error during OpenAI image request: {e!s}"
            logger.error(error_msg)
            return b64_data, price, error_msg

        if not response.data or not response.data[0].b64_json:
            error_msg = "OpenAI image request returned no image data"
            logger.error(error_msg)
            return b64_data, price, error_msg

        b64_data = response.data[0].b64_json
        logger.info("OpenAI image generation successful")
        return b64_data, price, error_msg

    async def translate(
        self, text: str, origin_language: Language, dest_language: Language
    ) -> tuple[str | None, float | None, str | None]:
        """Translate a text from one language to another using GPT."""
        messages = [
            {
                "role": "system",
                "content": (
                    f"You translate {origin_language.name} into {dest_language.name}. "
                    "Keep the original meaning and the pretentious contemporary-art gallery style: "
                    "slightly overwrought, theoretical, and self-serious. "
                    f"Write natural, correct {dest_language.name}. Translate titles and quoted work names too. "
                    "Return only the translated text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Translate this {origin_language.name} text into {dest_language.name}. "
                    "Keep its pretentious art-world tone and exact information. "
                    "Do not add commentary.\n\n"
                    f"{text}"
                ),
            },
        ]
        return await self._process_openai_request(messages)

    async def reformulate(
        self, text: str, language: Language | None = None
    ) -> tuple[str | None, float | None, str | None]:
        """Reformulate a text using GPT."""
        messages = [
            {
                "role": "system",
                "content": "Tu parles français et tu peux reformuler un texte français en gardant son style et son sens, mais en l'étoffant légèrement.",
            },
            {
                "role": "user",
                "content": f"Reformule ce texte en français en gardant son sens, ses informations exactes principales. Son style doit conserver le style original, c'est à dire celui d'un texte prétentieux de galerie d'art contemporain, mais il doit être légèrement étoffé et allongé, si possible autour de 50% plus long. Ne pas inclure dans ta réponse autre chose que le texte en lui-même. Voici le texte à reformuler: « {text} »",
            },
        ]
        result_text, price, error_msg = await self._process_openai_request(messages)

        # Additional processing specific to reformulation
        if result_text:
            if result_text[:1] in ["«", "“"]:
                result_text = result_text[2:]
            if result_text[-1:] in ["»", "”"]:
                result_text = result_text[:-2]
            result_text = result_text.strip()

        return result_text, price, error_msg

    def calculate_request_price(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the price of an OpenAI request.
        https://openai.com/blog/openai-api/
        https://openai.com/pricing/

        Args:
            model (dict): GPT model (see settings)
            input_tokens (int): number of tokens in the input
            output_tokens (int): number of tokens in the output

        Returns:
            float: price of the request
        """
        price: float = (self.model["pricing"]["input_per_1M"] * (input_tokens / 1000000)) + (
            self.model["pricing"]["output_per_1M"] * (output_tokens / 1000000)
        )
        return price
