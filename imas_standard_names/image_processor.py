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
    image_dir: str = "docs/img"

    EXTENSION_MAP: ClassVar[Dict[str, str]] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "image/webp": "webp",
    }

    def __post_init__(self):
        """Ensure image_dir is a Path object."""
        self.image_dir = Path(self.image_dir)

    @cached_property
    def urls(self) -> List[str]:
        """Return GitHub user-attachment image URLs extracted from documentation."""
        return re.findall(
            r"https://github.com/user-attachments/assets[^)]*", self.documentation
        )

    @cached_property
    def files(self) -> List[Path]:
        """Return a list of Path objects where images will be stored locally."""
        return [self._filename(url, index) for index, url in enumerate(self.urls, 1)]

    def _extension(self, url: str) -> str:
        """Determine file extension for an image URL based on its content type."""
        response = requests.get(url, stream=True)
        content_type = response.headers.get("content-type")
        if not content_type or not content_type.startswith("image/"):
            # Fallback to Python's mimetypes if HTTP header is not helpful
            content_type, _ = mimetypes.guess_type(url)
        return self.EXTENSION_MAP.get(content_type, "png")  # Default to png as fallback

    def _filename(self, url: str, index: int) -> Path:
        """Determine the full path where the downloaded image will be stored."""
        filename = f"{self.standard_name}-{index}"
        extension = self._extension(url)
        return (self.image_dir / filename).with_suffix(f".{extension}")

    def _download_image(self, url: str, filepath: int) -> str:
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

    def download_images(self):
        """Download images from URLs and save them to local paths."""
        self.image_dir.mkdir(parents=True, exist_ok=True)
        for url, filepath in zip(self.urls, self.files):
            self._download_image(url, filepath)

    def documentation_with_relative_paths(self):
        """Return documentation with relative image paths."""
        documentation = self.documentation
        for url, filepath in zip(self.urls, self.files):
            relative_path = filepath.relative_to(self.image_dir.parent)
            documentation = documentation.replace(url, str(relative_path))
        return documentation
