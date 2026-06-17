import asyncio
import json

import niquests

from blockhaus101.settings import GETIMGAI_API_KEY, GETIMGAI_API_URL, logger


class GetImgAiAPI:
    def __init__(self) -> None:
        self.api_key = GETIMGAI_API_KEY
        self.base_url = GETIMGAI_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "accept": "application/json",
        }

    async def _get(self, endpoint: str, params: dict | None = None) -> dict | list | None:
        """Sends a GET request to the GetImgAI API."""
        logger.debug(f"Sending GET request to {self.base_url}{endpoint}")
        async with niquests.AsyncSession() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}", headers=self.headers, params=params
            )
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response text: {response.text}")

            if response.status_code == 401:
                logger.error("Authentication failed - check your API key")
                return None

            try:
                data = json.loads(response.text)
                if "error" in data:
                    logger.error(f"API error: {data['error']}")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                return None

    async def _post(self, endpoint: str, data: dict, added_headers: dict | None) -> dict | None:
        """Sends a POST request to the GetImgAI API."""
        async with asyncio.timeout(30):  # Default timeout to 30 seconds
            headers = self.headers
            if added_headers:
                headers.update(added_headers)
            async with niquests.AsyncSession() as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}", headers=headers, json=data
                )
            # response.raise_for_status() # TODO: uncomment this line
            if response.status_code and response.text:
                return json.loads(response.text)
            return None

    async def get_models(
        self, family: str | None = "stable-diffusion-xl", pipeline: str | None = "text-to-image"
    ) -> list | None:
        """Get available models from GetImg.AI API.
        More info on https://docs.getimg.ai/reference/getmodels

        Available families:
        - stable-diffusion-xl: High resolution (1024x1024) models
        - stable-diffusion: Standard resolution (512x512) models

        Available pipelines:
        - text-to-image
        - image-to-image
        - ip-adapter
        - inpaint (some models only)
        """
        return await self._get(endpoint="models", params={"family": family, "pipeline": pipeline})

    async def essential_v2(
        self,
        prompt: str,
        style: str = "photorealism",
        aspect_ratio: str = "1:1",
        output_format: str = "jpeg",
        response_format: str = "b64",
    ) -> dict | None:
        """Generate images using the Essential v2 model.

        A simplified API with preset styles. Good for quick results
        but less control than SD or SDXL models.

        Available styles:
        - photorealism
        - anime
        - artistic
        - illustration
        - digital-art
        - etc.

        Args:
            prompt: Text description of the desired image
            style: Preset style to apply
            aspect_ratio: "1:1", "16:9", "9:16", etc.
            output_format: "jpeg" or "png"
            response_format: "b64" or "url"

        Returns:
            dict with 'image' (base64 string) and 'cost', or None if failed
        """
        added_headers = {"content-type": "application/json"}
        data = {
            "style": style,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": output_format,
            "response_format": response_format,
        }
        return await self._post(
            endpoint="essential-v2/text-to-image",
            data=data,
            added_headers=added_headers,
        )  # type: ignore

    async def stable_diffusion_xl(
        self,
        prompt: str,
        model: str = "realvis-xl-v4",
        negative_prompt: str | None = None,
        prompt_2: str | None = None,
        negative_prompt_2: str | None = None,
        width: int = 1024,  # can be 256 to 1536
        height: int = 1024,  # can be 256 to 1536
        steps: int = 30,
        guidance: float = 7.5,
        seed: int = 0,
        scheduler: str = "euler",
        output_format: str = "jpeg",
        response_format: str = "b64",
    ) -> dict | None:
        """Generate images using Stable Diffusion XL models.

        Available models:
        - realvis-xl-v4: RealVisXL V4.0 - Specialized in photorealistic results
        - juggernaut-xl-v10: JuggernautXL X - Good for architectural and detailed scenes
        - reproduction-v3-31: Reproduction v3.31 - Balanced model for various styles
        - stable-diffusion-xl-v1-0: Original SDXL - Base model with inpainting support

        All models support 1024x1024 base resolution and cost $0.000075 per image.

        Args:
            prompt: Text description of the desired image
            model: Model ID to use
            negative_prompt: Things to avoid in the image
            prompt_2: Secondary prompt for refinement (optional)
            negative_prompt_2: Secondary negative prompt (optional)
            width: Image width (256-1536)
            height: Image height (256-1536)
            steps: Number of denoising steps (1-100)
            guidance: How strictly to follow the prompt (0-20)
            seed: Random seed for reproducibility
            scheduler: Denoising scheduler ("euler", "dpmpp_2m", etc.)
            output_format: "jpeg" or "png"
            response_format: "b64" or "url"

        Returns:
            dict with 'image' (base64 string) and 'cost', or None if failed
        """
        logger.debug("Preparing SDXL API request...")
        added_headers = {"content-type": "application/json"}
        data = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "prompt_2": prompt_2,
            "negative_prompt_2": negative_prompt_2,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance": guidance,
            "seed": seed,
            "scheduler": scheduler,
            "output_format": output_format,
            "response_format": response_format,
        }
        logger.debug(f"Sending request to SDXL API with steps={steps}, guidance={guidance}")

        try:
            response = await self._post(
                endpoint="stable-diffusion-xl/text-to-image", data=data, added_headers=added_headers
            )
            if response:
                logger.debug("SDXL API request successful")
                logger.debug(f"Response keys: {response.keys()}")
                return response
            logger.debug("SDXL API request failed - no response")
            return None
        except Exception as e:
            logger.debug(f"SDXL API request failed with error: {str(e)}")
            return None

    async def stable_diffusion(
        self,
        prompt: str,
        model: str = "stable-diffusion-v1-5",
        negative_prompt: str = "photorealism",
        prompt_2: str | None = None,
        negative_prompt_2: str | None = None,
        width: int = 512,
        height: int = 512,
        steps: int = 25,
        guidance: float = 7.5,
        seed: int = 0,
        scheduler: str = "dpmsolver++",
        output_format: str = "jpeg",
        response_format: str = "b64",
    ) -> dict | None:
        """Generate images using standard Stable Diffusion models.

        Available models:
        - stable-diffusion-v1-5: Original SD 1.5
        - stable-diffusion-v2-1: Improved SD 2.1 (768x768)
        - realistic-vision-v5-1: Specialized in realistic images
        - dream-shaper-v8: All-purpose with good quality
        - absolute-reality-v1-8-1: Focused on realistic renders

        Most models support 512x512 base resolution and cost $0.000075 per image.

        Args:
            prompt: Text description of the desired image
            model: Model ID to use
            negative_prompt: Things to avoid in the image
            prompt_2: Secondary prompt for refinement (optional)
            negative_prompt_2: Secondary negative prompt (optional)
            width: Image width (256-1024)
            height: Image height (256-1024)
            steps: Number of denoising steps (1-100)
            guidance: How strictly to follow the prompt (0-20)
            seed: Random seed for reproducibility
            scheduler: Denoising scheduler ("euler", "dpmpp_2m", etc.)
            output_format: "jpeg" or "png"
            response_format: "b64" or "url"

        Returns:
            dict with 'image' (base64 string) and 'cost', or None if failed
        """
        added_headers = {"content-type": "application/json"}
        data = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "prompt_2": prompt_2,
            "negative_prompt_2": negative_prompt_2,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance": guidance,
            "seed": seed,
            "scheduler": scheduler,
            "output_format": output_format,
            "response_format": response_format,
        }
        return await self._post(
            endpoint="stable-diffusion/text-to-image", data=data, added_headers=added_headers
        )  # type: ignore

    async def latent_consistency(
        self,
        prompt: str,
        negative_prompt: str,
        model: str = "lcm-dream-shaper-v8",
        width: int = 512,  # can be 256 to 1024
        height: int = 512,  # can be 256 to 1024
        steps: int = 4,  # 1 to 8. The number of denoising steps. More steps usually can produce higher quality images, but take more time to generate.
        seed: int = 0,  # 0 to 2147483647. Random seed for the model.
        output_format: str = "jpeg",  # can be "jpeg" or "png"
        response_format: str = "b64",  # can be "b64" or "url"
    ) -> dict | None:
        """https://docs.getimg.ai/reference/poststablediffusionxltexttoimage"""
        added_headers = {"content-type": "application/json"}
        data = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "seed": seed,
            "output_format": output_format,
            "response_format": response_format,
        }
        return await self._post(
            endpoint="latent-consistency/text-to-image", data=data, added_headers=added_headers
        )  # type: ignore
