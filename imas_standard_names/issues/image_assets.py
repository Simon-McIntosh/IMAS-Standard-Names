"""Processing of image assets embedded in GitHub issue submission documentation.

This module was extracted from the previous top-level image_processor module.
Backwards compatibility with the old import path is intentionally not preserved.
"""

from __future__ import annotations

import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import ClassVar

import requests


@dataclass
class ImageProcessor:
    """Extract and materialize remote image references in documentation.

    Given a documentation string in markdown (possibly containing HTML <img> tags),
    this class:
      * Extracts image source URLs
      * Determines local file paths (with appropriate extensions)
      * Downloads the assets to a target directory
      * Rewrites the documentation to use relative paths
    """

    standard_name: str
    documentation: str
    image_dir: Path = Path("docs/img")
    parents: int | None = 0  # number of parent levels to relativize against

    EXTENSION_MAP: ClassVar[dict[str, str]] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "image/webp": "webp",
    }

    @cached_property
    def urls(self) -> list[str]:
        """Return image URLs extracted from documentation markdown/HTML."""
        markdown_pattern = r"!\[[^\]]*\]\((https?://[^)\s]+)\)"
        urls = re.findall(markdown_pattern, self.documentation)
        html_pattern = r"<img[^>]*src=[\'\"]([^\'\">]+)[\'\"][^>]*>"
        html_urls = re.findall(html_pattern, self.documentation)
        return urls + html_urls

    @cached_property
    def paths(self) -> list[Path]:
        """List of Path objects where images will be stored locally."""
        return [self._filepath(url, index) for index, url in enumerate(self.urls, 1)]

    # Internal helpers -------------------------------------------------
    def _extension(self, url: str) -> str:
        # 1. Prefer explicit extension in the URL to avoid unnecessary network calls
        url_ext = Path(url).suffix.lower().lstrip(".")
        if url_ext in self.EXTENSION_MAP.values():
            return url_ext
        # 2. Try mimetype guess (cheap, local)
        content_type, _ = mimetypes.guess_type(url)
        if content_type and content_type in self.EXTENSION_MAP:
            return self.EXTENSION_MAP[content_type]
        # 3. Fall back to HTTP request (may be disabled in test environments)
        try:
            response = requests.get(url, stream=True, timeout=5)
            content_type = response.headers.get("content-type")
            if content_type and content_type in self.EXTENSION_MAP:
                return self.EXTENSION_MAP[content_type]
        except Exception:
            pass
        # 4. Final fallback
        return "png"

    def _filepath(self, url: str, index: int) -> Path:
        filename = f"{self.standard_name}-image{index}"
        extension = self._extension(url)
        return (self.image_dir / filename).with_suffix(f".{extension}")

    def _download_image(self, url: str, filepath: Path) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        response = requests.get(url, stream=True)
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        os.replace(temp_path, filepath)

    # Public API -------------------------------------------------------
    def download_images(self, remove_existing: bool = False) -> None:
        self.image_dir.mkdir(parents=True, exist_ok=True)
        if remove_existing:
            for file in self.image_dir.glob("*"):
                if file.is_file():
                    file.unlink()
        for url, filepath in zip(self.urls, self.paths, strict=False):
            self._download_image(url, filepath)

    def relative_path(self, filepath: Path) -> Path:
        if self.parents:
            return filepath.relative_to(self.image_dir.parents[self.parents])
        return filepath

    def documentation_with_relative_paths(self) -> str:
        documentation = self.documentation
        for url, filepath in zip(self.urls, self.paths, strict=False):
            filepath = self.relative_path(filepath)
            documentation = documentation.replace(url, filepath.as_posix())
        return documentation
