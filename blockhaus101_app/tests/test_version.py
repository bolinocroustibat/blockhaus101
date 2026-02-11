"""Tests for dynamic versioning (setuptools-scm) and app metadata."""

import re
import unittest
from pathlib import Path

from setuptools_scm import get_version

# Project root (directory containing pyproject.toml and .git)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _semver_like_pattern() -> re.Pattern[str]:
    """Match setuptools-scm versions: 1.2.3, 1.2.3.dev0, 1.2.3.dev0+gabc1234, 1.2.3+gabc1234."""
    return re.compile(
        r"^\d+\.\d+\.\d+"  # major.minor.patch
        r"(\.dev\d+)?"  # optional .devN
        r"(\+g[a-f0-9]+(\.[a-z0-9]+)?)?"  # optional +g<sha> or +g<sha>.dirty
        r"$",
        re.IGNORECASE,
    )


class TestDynamicVersioning(unittest.TestCase):
    """Test that setuptools-scm resolves version from Git and that app metadata matches."""

    def test_setuptools_scm_resolves_version_from_git(self) -> None:
        """get_version() from repo root returns a valid semver-like string."""
        version = get_version(root=str(_PROJECT_ROOT))
        self.assertIsInstance(version, str)
        self.assertNotEqual(version, "")
        self.assertRegex(
            version,
            _semver_like_pattern(),
            msg=f"Version {version!r} does not match expected semver-like pattern",
        )

    def test_installed_package_metadata_matches_scm_version(self) -> None:
        """When the project is installed, package metadata version matches setuptools-scm."""
        import importlib.metadata

        try:
            meta = importlib.metadata.metadata("blockhaus101")
        except importlib.metadata.PackageNotFoundError:
            self.skipTest("blockhaus101 not installed as package (e.g. not in venv)")
        installed_version = meta["Version"]
        scm_version = get_version(root=str(_PROJECT_ROOT))
        self.assertEqual(
            installed_version,
            scm_version,
            msg="Installed package version should match setuptools-scm (same repo state)",
        )

    def test_settings_version_from_metadata(self) -> None:
        """APP_NAME and VERSION in settings come from package metadata when installed."""
        from blockhaus101.settings import APP_NAME, VERSION

        self.assertEqual(APP_NAME, "blockhaus101")
        self.assertIsInstance(VERSION, str)
        self.assertNotEqual(VERSION, "")
        if VERSION != "unknown":
            self.assertRegex(VERSION, _semver_like_pattern(), msg=f"VERSION {VERSION!r} invalid")
