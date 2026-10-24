"""Reference pricing for image generation models (USD).

This module is documentation for humans and for choosing models in settings.
It is not used for billing: GetImg returns ``usage.total_cost`` on each response;
OpenAI image cost is token-based and not computed in ``OpenAiAPI.generate_image`` yet.

Sources (Oct 2026):
- OpenAI: https://openai.com/pricing/
- GetImg.AI: https://getimg.ai/developers/ai-image-generator-api
  Live rates: ``GET https://api.getimg.ai/v2/models/{model}``
"""

# OpenAI Image API — price per 1M tokens (input / output).
OPENAI_IMAGE_MODELS_PRICING: dict[str, dict] = {
    "chatgpt-image-latest": {"input_per_1M": 5.0, "output_per_1M": 32.0},
    "gpt-image-1": {"input_per_1M": 5.0, "output_per_1M": 40.0},
    "gpt-image-1.5": {"input_per_1M": 5.0, "output_per_1M": 32.0},
    "gpt-image-1-mini": {"input_per_1M": 2.0, "output_per_1M": 8.0},
    "gpt-image-2": {"input_per_1M": 5.0, "output_per_1M": 30.0},
    "gpt-image-2-2026-04-21": {"input_per_1M": 5.0, "output_per_1M": 30.0},
    "gpt-image-2.5-flare": {"input_per_1M": 5.0, "output_per_1M": 30.0},
    "gpt-image-2.5-flare-2026-09-08": {"input_per_1M": 5.0, "output_per_1M": 30.0},
    "gpt-image-2.5-sunburst": {"input_per_1M": 5.0, "output_per_1M": 30.0},
    "gpt-image-2.5-sunburst-2026-09-08": {"input_per_1M": 5.0, "output_per_1M": 30.0},
}

# GetImg.AI — starting price per image (lowest tier); actual cost depends on resolution.
GETIMGAI_IMAGE_MODELS_PRICING: dict[str, dict] = {
    "gemini-nano-banana-2-1": {
        "name": "Nano Banana 2.1",
        "vendor": "google",
        "added": "2026-10",
        "from_price_per_image_usd": 0.04,
        "max_resolution": "4K",
        "reference_images_max": 14,
    },
    "gpt-image-2.5-flare": {
        "name": "GPT Image 2.5 Flare",
        "vendor": "openai",
        "added": "2026-09",
        "from_price_per_image_usd": 0.06,
        "max_resolution": "2K",
        "reference_images_max": 10,
    },
    "gpt-image-2.5-sunburst": {
        "name": "GPT Image 2.5 Sunburst",
        "vendor": "openai",
        "added": "2026-09",
        "from_price_per_image_usd": 0.06,
        "max_resolution": "2K",
        "reference_images_max": 10,
    },
    "seedream-5-pro": {
        "name": "Seedream 5.0 Pro",
        "vendor": "bytedance",
        "added": "2026-09",
        "from_price_per_image_usd": 0.05,
        "max_resolution": "2K",
        "reference_images_max": 10,
    },
    "qwen-image-3-0-pro": {
        "name": "Qwen Image 3.0 Pro",
        "vendor": "alibaba",
        "added": "2026-09",
        "from_price_per_image_usd": 0.04,
        "max_resolution": "2K",
        "reference_images_max": 3,
    },
    "grok-imagine-image-2.0": {
        "name": "Grok Imagine Image 2.0",
        "vendor": "xai",
        "added": "2026-08",
        "from_price_per_image_usd": 0.09,
        "max_resolution": "2K",
        "reference_images_max": 3,
    },
    "gemini-3-1-flash-lite-image": {
        "name": "Nano Banana 2 Lite",
        "vendor": "google",
        "added": "2026-06",
        "from_price_per_image_usd": 0.035,
        "max_resolution": "1K",
        "reference_images_max": 3,
    },
    "grok-imagine-image": {
        "name": "Grok Imagine Image",
        "vendor": "xai",
        "added": "2026-06",
        "from_price_per_image_usd": 0.03,
        "max_resolution": "2K",
        "reference_images_max": 3,
    },
    "qwen-image-2-0": {
        "name": "Qwen Image 2.0",
        "vendor": "alibaba",
        "added": "2026-04",
        "from_price_per_image_usd": 0.035,
        "max_resolution": "2K",
        "reference_images_max": 3,
    },
    "qwen-image-2-0-pro": {
        "name": "Qwen Image 2.0 Pro",
        "vendor": "alibaba",
        "added": "2026-04",
        "from_price_per_image_usd": 0.075,
        "max_resolution": "2K",
        "reference_images_max": 3,
    },
    "wan-2-7-image-pro": {
        "name": "Wan 2.7 Image Pro",
        "vendor": "alibaba",
        "added": "2026-04",
        "from_price_per_image_usd": 0.075,
        "max_resolution": "2K",
        "reference_images_max": 9,
    },
    "wan-2-7-image": {
        "name": "Wan 2.7 Image",
        "vendor": "alibaba",
        "added": "2026-04",
        "from_price_per_image_usd": 0.03,
        "max_resolution": "2K",
        "reference_images_max": 9,
    },
    "gpt-image-2": {
        "name": "GPT Image 2",
        "vendor": "openai",
        "added": "2026-04",
        "from_price_per_image_usd": 0.06,
        "max_resolution": "2K",
        "reference_images_max": 10,
    },
    "gemini-3-1-flash-image": {
        "name": "Nano Banana 2",
        "vendor": "google",
        "added": "2026-02",
        "from_price_per_image_usd": 0.08,
        "max_resolution": "4K",
        "reference_images_max": 4,
    },
    "seedream-5-lite": {
        "name": "Seedream 5.0 Lite",
        "vendor": "bytedance",
        "added": "2026-02",
        "from_price_per_image_usd": 0.035,
        "max_resolution": "2K",
        "reference_images_max": 10,
    },
    "z-image-turbo": {
        "name": "Z-Image Turbo",
        "vendor": "alibaba",
        "added": "2025-12",
        "from_price_per_image_usd": 0.015,
        "max_resolution": "1K",
        "reference_images_max": None,
    },
    "seedream-4-5": {
        "name": "Seedream 4.5",
        "vendor": "bytedance",
        "added": "2025-12",
        "from_price_per_image_usd": 0.04,
        "max_resolution": "4K",
        "reference_images_max": 10,
    },
    "seedream-4": {
        "name": "Seedream 4",
        "vendor": "bytedance",
        "added": "2025-11",
        "from_price_per_image_usd": 0.03,
        "max_resolution": "4K",
        "reference_images_max": 10,
    },
}
