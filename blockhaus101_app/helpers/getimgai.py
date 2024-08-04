import json

import requests

from blockhaus101.settings import GETIMGAI_API_KEY, GETIMGAI_API_URL


class GetImgAiAPI:
    def __init__(self) -> None:
        self.api_key = GETIMGAI_API_KEY
        self.base_url = GETIMGAI_API_URL
        self.headers = {
            "Authorization": "Bearer {self.api_key}",
            "accept": "application/json",
        }

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list | None:
        """Sends a GET request to the GetImgAI API."""
        response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params)
        # response.raise_for_status() #TODO: uncomment this line
        if response.status_code == 200 and response.text:
            return json.loads(response.text)
        return None

    def _post(self, endpoint: str, data: dict, added_headers: dict | None) -> dict | None:
        """Sends a POST request to the GetImgAI API."""
        headers = self.headers
        if added_headers:
            headers.update(added_headers)
        response = requests.post(f"{self.base_url}{endpoint}", headers=headers, json=data)
        # response.raise_for_status() #TODO: uncomment this line
        if response.status_code and response.text:
            return json.loads(response.text)
        return None

    def get_models(self, family: str | None = None, pipeline: str | None = None) -> list | None:
        """https://docs.getimg.ai/reference/getmodels
        e.g. family="text-to-image", pipeline="stable-diffusion-xl"
        e.g. family="text-to-image", pipeline="essential-v2"
        """
        return self._get(endpoint="models", params={"family": family, "pipeline": pipeline})  # type: ignore

    def essential_v2(
        self,
        prompt: str,
        style: str = "photorealism",
        aspect_ratio: str = "1:1",
        output_format: str = "png",  # can be "jpeg" or "png"
        response_format: str = "b64",  # can be "b64" or "url"
    ) -> dict | None:
        """https://docs.getimg.ai/reference/postessentialv2texttoimage"""
        added_headers = {"content-type": "application/json"}
        data = {
            "style": style,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": output_format,
            "response_format": response_format,
        }
        return self._post(
            endpoint="essential-v2/text-to-image", data=data, added_headers=added_headers
        )  # type: ignore

    def stable_diffusion_xl(
        self,
        prompt: str,
        negative_prompt: str,
        model: str = "stable-diffusion-xl-v1-0",
        prompt_2: str | None = None,
        negative_prompt_2: str | None = None,
        width: int = 1024,  # can be 256 to 1536
        height: int = 1024,  # can be 256 to 1536
        steps: int = 30,  # 1 to 100. The number of denoising steps. More steps usually can produce higher quality images, but take more time to generate.
        guidance: float = 7.5,  # 0 to 20. Guidance scale as defined in Classifier-Free Diffusion Guidance. Higer guidance forces the model to better follow the prompt, but result in lower quality output.
        seed: int = 0,  # 0 to 2147483647. Random seed for the model.
        scheduler: str = "euler",  #  Scheduler used to denoise the encoded image latents.
        output_format: str = "png",  # can be "jpeg" or "png"
        response_format: str = "b64",  # can be "b64" or "url"
    ) -> dict | None:
        """https://docs.getimg.ai/reference/poststablediffusionxltexttoimage"""
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
        return self._post(
            endpoint="stable-diffusion-xl/text-to-image", data=data, added_headers=added_headers
        )  # type: ignore

    def stable_diffusion(
        self,
        prompt: str,
        model: str = "stable-diffusion-v1-5",
        negative_prompt: str = "photorealism",
        prompt_2: str | None = None,
        negative_prompt_2: str | None = None,
        width: int = 512,  # can be 256 to 1024
        height: int = 512,  # can be 256 to 1024
        steps: int = 25,  # 1 to 100. The number of denoising steps. More steps usually can produce higher quality images, but take more time to generate.
        guidance: float = 7.5,  # 0 to 20. Guidance scale as defined in Classifier-Free Diffusion Guidance. Higer guidance forces the model to better follow the prompt, but result in lower quality output.
        seed: int = 0,  # 0 to 2147483647. Random seed for the model.
        scheduler: str = "dpmsolver++",  #  Scheduler used to denoise the encoded image latents.
        output_format: str = "png",  # can be "jpeg" or "png"
        response_format: str = "b64",  # can be "b64" or "url"
    ) -> dict | None:
        """https://docs.getimg.ai/reference/poststablediffusionxltexttoimage"""
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
        return self._post(
            endpoint="stable-diffusion/text-to-image", data=data, added_headers=added_headers
        )  # type: ignore

    def latent_consistency(
        self,
        prompt: str,
        negative_prompt: str,
        model: str = "lcm-dream-shaper-v8",
        width: int = 512,  # can be 256 to 1024
        height: int = 512,  # can be 256 to 1024
        steps: int = 4,  # 1 to 8. The number of denoising steps. More steps usually can produce higher quality images, but take more time to generate.
        seed: int = 0,  # 0 to 2147483647. Random seed for the model.
        output_format: str = "png",  # can be "jpeg" or "png"
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
        return self._post(
            endpoint="latent-consistency/text-to-image", data=data, added_headers=added_headers
        )  # type: ignore
