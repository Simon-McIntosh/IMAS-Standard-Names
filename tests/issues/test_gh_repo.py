import contextlib
import itertools
import pytest

from imas_standard_names.issues.gh_repo import Repository


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/username/repository.git",
        "git@github.com:username/repository.git",
    ],
)
def test_repository_owner_name(url):
    repo = Repository(remote_url=url)
    assert repo.owner == "username"
    assert repo.name == "repository"


def test_repository_owner_error():
    with pytest.raises(ValueError) as excinfo:
        Repository(remote_url="somewhere://github.com/username/repository.git")
    assert "Could not parse GitHub URL format" in str(excinfo.value)


def test_repository_name_error():
    with pytest.raises(ValueError) as excinfo:
        Repository(remote_url="https://github.com/username/repo/subrepo")
    assert "Could not parse GitHub URL format" in str(excinfo.value)


def test_remote_url():
    repo = Repository()
    assert repo.remote_url.startswith("https://") or repo.remote_url.startswith("git@")


def test_remote_url_error(tmp_path):
    remote = "origin"
    with contextlib.chdir(tmp_path), pytest.raises(NotADirectoryError) as excinfo:
        Repository(remote=remote)
    assert f"Not a git repository or no remote named {remote}" in str(excinfo.value)


def test_no_remote_error():
    remote = "upriver"
    with pytest.raises(NotADirectoryError) as excinfo:
        Repository(remote=remote)
    assert f"Not a git repository or no remote named {remote}" in str(excinfo.value)


def url(scheme, owner, repository):
    if scheme == "ssh":
        return f"git@github.com:{owner}/{repository}"
    return f"{scheme}://github.com/{owner}/{repository}"


@pytest.mark.parametrize(
    "scheme, owner",
    itertools.product(
        ["https", "ssh"],
        ["anotheruser", "iter-organization"],
    ),
)
def test_remote_regex_match(scheme, owner):
    remote_url = url(scheme, owner, "IMAS-Standard-Names")
    repo = Repository(remote_url=remote_url)
    assert repo.remote_regex.match(remote_url)


def test_pages_regex_match():
    remote_url = "git@github.com:username/repository.git"
    repo = Repository(remote_url=remote_url)
    assert repo.pages_regex.match("https://username.github.io/repository")


def test_remote_regex_match_other_repo():
    repo_url = url("ssh", "iter-organization", "IMAS-Standard-Names")
    remote_url = url("ssh", "iter-organization", "IMAS-Standard-Interfaces")
    repo = Repository(remote_url=repo_url)
    assert not repo.remote_regex.match(remote_url)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
