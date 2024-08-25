import base64
import io
from pathlib import Path

from PIL import Image

from blockhaus101.settings import logger


def save_b64_img(img_b64_data: str, filename: str, format: str = "png") -> Path:
    """Save an b64 image data into a file, and return the path to the file"""
    app_path = Path(__file__).resolve().parent.parent
    filepath: Path = app_path / "static/images" / f"{filename}.{format}"
    img_bytes: bytes = base64.b64decode(img_b64_data, validate=True)
    with open(filepath, "wb") as file:
        file.write(img_bytes)
    return filepath


def decode_b64_img(img_b64_data: str) -> Image:
    try:
        img_bytes: bytes = base64.b64decode(img_b64_data.encode("UTF-8"))
        buf = io.BytesIO(img_bytes)
        image = Image.open(buf)
        return image
    except Exception as e:
        logger.error(f"Error while decoding image: {e}")
        return None
