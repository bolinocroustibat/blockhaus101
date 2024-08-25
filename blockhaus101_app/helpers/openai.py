from openai import AsyncOpenAI

from blockhaus101.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_MODELS,
    OPENAI_SYSTEM_PROMPT,
    OPENAI_USER_PROMPT,
    logger,
)


class OpenAiAPI:
    def __init__(self):
        try:
            self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            self.model: dict = next(
                (model for model in OPENAI_MODELS if model["model-name"] == OPENAI_MODEL)
            )
            self.system_prompt = OPENAI_SYSTEM_PROMPT
            self.user_prompt = OPENAI_USER_PROMPT
        except Exception:
            error_msg = "La configuration OpenAI n'est pas valide. OpenAI API key, OpenAI system prompt et OpenAI user prompt ont-ils bien été configurés dans les réglages ?"  # noqa: E501
            logger.error(error_msg)
            return error_msg

    @property
    def model_friendly_name(self) -> str:
        return self.model["friendly-name"]

    async def reformulate(self, html_text: str) -> tuple[str | None, float | None, str | None]:
        """Reformulate a text using GPT.

        Args:
            html_text (str): _description_

        Returns:
            str: reformulated HTML text
            float: price of the request
            str: error message (if any)

        TODO: Use langchain instead of OpenAI:
        https://python.langchain.com/en/latest/getting_started/getting_started.html
        """

        reformulated_text: str | None = None
        price: float | None = None
        error_msg: str | None = None

        # Initialize OpenAI
        # openai.organization = OPENAI_ORGANIZATION
        self.client.api_key = self.api_key

        # Request OpenAI
        logger.info("Requesting OpenAI to reformulate text...")
        messages: list[dict] = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {
                "role": "user",
                "content": self.user_prompt.format(html_text=html_text),
            },
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model["model-name"],
                messages=messages,
                user="warning-trading",
            )
        except Exception as e:
            error_msg = f"Erreur lors de la requête OpenAI : {str(e)}"
            logger.error(error_msg)
        else:
            # logger.debug(response)

            if response.choices[0].finish_reason == "length":
                # https://platform.openai.com/docs/guides/gpt/chat-completions-response-format
                error_msg = "Le texte est trop long pour ce modèle, veuillez utiliser un autre modèle dans les réglages."  # noqa: E501
                logger.error(error_msg)

            else:
                # Calculate the price of the request
                try:
                    tokens_usage: int = response.usage.total_tokens
                    price = self.calculate_request_price(
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                    )
                    logger.info(f"\nTokens used: {tokens_usage}. OpenAI request price: {price}$")
                except Exception as e:
                    logger.error(f"\nUnable to calculate the price of the request: {str(e)}")

                reformulated_text = response.choices[0].message.content

                # Strip the reformulated text from the quotes
                if reformulated_text:
                    if reformulated_text[:1] == "«":
                        reformulated_text = reformulated_text[2:]
                    if reformulated_text[-1:] == "»":
                        reformulated_text = reformulated_text[:-2]
                    reformulated_text = reformulated_text.strip()

        return (reformulated_text, price, error_msg)

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
        price: float = (self.model["price_input_per_1M"] * (input_tokens / 1000000)) + (
            self.model["price_output_per_1M"] * (output_tokens / 1000000)
        )
        return price
