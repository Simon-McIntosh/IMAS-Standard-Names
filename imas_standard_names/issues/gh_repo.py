# GitHub repo URL utilities
import re
import subprocess
from dataclasses import dataclass
from functools import cached_property


@dataclass
class Repository:
    remote: str = "origin"
    remote_url: str | None = None

    def __post_init__(self):
        if not self.remote_url:
            self.remote_url = self._remote_url()
        self.owner = self._parse_owner()
        self.name = self._parse_name()

    @cached_property
    def remote_regex(self) -> re.Pattern:
        return re.compile(
            rf"(https://github\.com/[\w\-]+/{self.name}|"  # https
            rf"git@github\.com:[\w\-]+/{self.name})"  # ssh
        )

    @cached_property
    def pages_regex(self) -> re.Pattern:
        return re.compile(rf"https://[\w\-]+\.github.io/{self.name}")

    @property
    def pages_url(self) -> str:
        return f"https://{self.owner}.github.io/{self.name}"

    def _remote_url(self):
        try:
            return (
                subprocess.check_output(
                    ["git", "config", "--get", f"remote.{self.remote}.url"],
                    text=True,
                    stderr=subprocess.PIPE,
                )
                .strip()
                .replace(".git", "")
            )
        except subprocess.CalledProcessError as error:
            raise NotADirectoryError(
                f"Not a git repository or no remote named {self.remote}"
            ) from error

    def _parse_owner(self):
        match self.remote_url:
            case str(url) if url.startswith("https://"):
                return url.split("/")[3]
            case str(url) if url.startswith("git@"):
                return url.split(":")[1].split("/")[0]
        raise ValueError("Could not parse GitHub URL format")

    def _parse_name(self):
        match self.remote_url.split("/"):
            case [*root, str(name)] if len(root) == 4 or len(root) == 1:
                return name.split(".")[0]
        raise ValueError("Could not parse GitHub URL format")


def update_static_urls(filename: str, remote: str | None):
    repo = Repository(remote=remote)
    with open(filename, encoding="utf-8") as f:
        content = f.read()
    _content = repo.remote_regex.sub(repo.remote_url, content)
    _content = repo.pages_regex.sub(repo.pages_url, _content)
    if content != _content:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(_content)
            print(f"{filename} updated with remote url: {repo.remote_url}")
    else:
        print(f"No changes needed to {filename}")


__all__ = ["Repository", "update_static_urls"]
