"""Manipulate documentation strings containing GitHub user-attachment image URLs."""

from dataclasses import dataclass
from functools import cached_property
import mimetypes
import os
from pathlib import Path
import re
import tempfile
from typing import ClassVar, Dict, List

import requests


@dataclass
class ImageProcessor:
    """Manipulate documentation strings containing GitHub user-attachment image URLs."""

    standard_name: str
    documentation: str
    image_dir: Path = Path("docs/img")
    parents: int | None = 0

    EXTENSION_MAP: ClassVar[Dict[str, str]] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "image/webp": "webp",
    }

    @cached_property
    def urls(self) -> List[str]:
        """Return image URLs extracted from documentation markdown."""

        # Match standard markdown image syntax ![alt text](URL)
        markdown_pattern = r"!\[[^\]]*\]\((https?://[^)\s]+)\)"
        urls = re.findall(markdown_pattern, self.documentation)

        # Also match HTML img tags
        html_pattern = r'<img[^>]*src=[\'"]([^\'">]+)[\'"][^>]*>'
        html_urls = re.findall(html_pattern, self.documentation)

        return urls + html_urls

    @cached_property
    def paths(self) -> List[Path]:
        """Return a list of Path objects where images will be stored locally."""
        return [self._filepath(url, index) for index, url in enumerate(self.urls, 1)]

    def _extension(self, url: str) -> str:
        """Determine file extension for an image URL based on its content type."""
        response = requests.get(url, stream=True)
        content_type = response.headers.get("content-type")
        if not content_type or not content_type.startswith("image/"):
            # Fallback to Python's mimetypes if HTTP header is not helpful
            content_type, _ = mimetypes.guess_type(url)
        return self.EXTENSION_MAP.get(
            content_type or "", "png"
        )  # Default to png as fallback

    def _filepath(self, url: str, index: int) -> Path:
        """Determine the full path where the downloaded image will be stored."""
        filename = f"{self.standard_name}-image{index}"
        extension = self._extension(url)
        return (self.image_dir / filename).with_suffix(f".{extension}")

    def _download_image(self, url: str, filepath: Path) -> None:
        """Download a remote image from a documentation url to a local filepath."""

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        # Download the image
        response = requests.get(url, stream=True)
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Move the temp file to final location
        os.replace(temp_path, filepath)

    def download_images(self, remove_existing=False):
        """Download images from URLs and save them to local paths."""
        self.image_dir.mkdir(parents=True, exist_ok=True)
        if remove_existing:  # Remove existing files in directory
            for file in self.image_dir.glob("*"):
                if file.is_file():
                    file.unlink()
        for url, filepath in zip(self.urls, self.paths):
            self._download_image(url, filepath)

    def relative_path(self, filepath: Path) -> Path:
        """Return the relative path of the image file."""
        if self.parents:
            return filepath.relative_to(self.image_dir.parents[self.parents])
        return filepath

    def documentation_with_relative_paths(self):
        """Return documentation with relative image paths."""
        documentation = self.documentation
        for url, filepath in zip(self.urls, self.paths):
            filepath = self.relative_path(filepath)
            documentation = documentation.replace(url, filepath.as_posix())
        return documentation
