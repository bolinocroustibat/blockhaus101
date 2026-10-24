"""Unit tests for small helpers that do not call external services."""

import base64
import binascii
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from blockhaus101_app.helpers import get_client_ip, save_b64_img


class TestGetClientIp(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_uses_the_last_forwarded_address(self) -> None:
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.2"

        self.assertEqual(get_client_ip(request), "198.51.100.2")

    def test_falls_back_to_remote_addr(self) -> None:
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.0.2.10"
        request.META.pop("HTTP_X_FORWARDED_FOR", None)

        self.assertEqual(get_client_ip(request), "192.0.2.10")


class TestSaveB64Img(SimpleTestCase):
    def test_writes_decoded_bytes(self) -> None:
        payload = base64.b64encode(b"image-bytes").decode()

        with TemporaryDirectory() as tmp, patch("blockhaus101_app.helpers.img.MEDIA_ROOT", tmp):
            path = save_b64_img(payload, "sample", "png")
            self.assertEqual(path, Path(tmp) / "sample.png")
            self.assertEqual(path.read_bytes(), b"image-bytes")

    def test_rejects_invalid_base64(self) -> None:
        with TemporaryDirectory() as tmp, patch("blockhaus101_app.helpers.img.MEDIA_ROOT", tmp):
            self.assertRaises(binascii.Error, save_b64_img, "not-base64", "sample")
