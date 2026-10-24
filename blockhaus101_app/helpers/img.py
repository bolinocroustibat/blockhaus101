import base64
from pathlib import Path

from django.db.models.fields.files import ImageFieldFile

from blockhaus101.settings import MEDIA_ROOT


def save_b64_img(b64_data: str, filename: str, img_format: str = "jpeg") -> Path:
    """Save an b64 image data into a file, and return the path to the file"""
    filepath: Path = Path(MEDIA_ROOT) / f"{filename}.{img_format}"
    img_bytes: bytes = base64.b64decode(b64_data, validate=True)
    with filepath.open("wb") as file:
        file.write(img_bytes)
    return filepath


def image_size(image: ImageFieldFile | None) -> tuple[int | None, int | None]:
    """Pixel size of an image file, when it can be read."""
    if not image:
        return None, None
    try:
        width = image.width
        height = image.height
    except (OSError, ValueError):
        return None, None
    if not width or not height:
        return None, None
    return width, height
