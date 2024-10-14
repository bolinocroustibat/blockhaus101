import base64
from pathlib import Path

from blockhaus101.settings import MEDIA_ROOT


def save_b64_img(b64_data: str, filename: str, img_format: str = "png") -> Path:
    """Save an b64 image data into a file, and return the path to the file"""
    filepath: Path = MEDIA_ROOT / f"{filename}.{img_format}"
    img_bytes: bytes = base64.b64decode(b64_data, validate=True)
    with open(filepath, "wb") as file:
        file.write(img_bytes)
    return filepath
