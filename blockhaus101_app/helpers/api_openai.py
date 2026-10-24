from openai import AsyncOpenAI, OpenAIError

from base_data_app.models.language import Language
from blockhaus101.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    logger,
)


class OpenAiAPI:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL

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
                user="warning-trading",
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

    async def translate(
        self, text: str, origin_language: Language, dest_language: Language
    ) -> tuple[str | None, float | None, str | None]:
        """Translate a text from one language to another using GPT."""
        messages = [
            {
                "role": "system",
                "content": f"You are a translation engine, able to translate a text from {origin_language.name} to {dest_language.name}.",
            },
            {
                "role": "user",
                "content": f"Translate the following text from {origin_language.name} to {dest_language.name}. Please return only the translated text, without any other sign, comment or explanation:\n{text}",
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
                "content": "Tu parles français et tu peux reformuler un texte français en gradant son style et son sens, mais en l'étoffant légèrement.",
            },
            {
                "role": "user",
                "content": f"Je souhaite que tu reformules ce texte en français en gardant son sens, ses informations exactes principales. Son style doit converser le style original, c'est à dire celui d'un texte artistique un peu prétentieux, mais il doit être légèrement étoffé et allongé, si possible autour de 50% plus long. Ne pas inclure dans ta réponse autre chose que le texte en lui-même. Voici le texte à reformuler: « {text} »",
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
