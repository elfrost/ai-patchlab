"""Tests for the git URL source acquisition module."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scanner.git_source import (
    GitCloneError,
    cloned_repo,
    is_valid_git_url,
)


class TestIsValidGitUrl:
    """Cheap URL shape validation before invoking `git`."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "http://example.com/repo.git",
            "git@github.com:owner/repo.git",
            "https://gitlab.com/group/sub/project",
        ],
    )
    def test_accepts_valid_urls(self, url: str) -> None:
        assert is_valid_git_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "   ",
            "owner/repo",
            "not a url",
            "ftp://example.com/repo",
            "../local/path",
            "file:///tmp/repo",
        ],
    )
    def test_rejects_invalid_urls(self, url: str) -> None:
        assert is_valid_git_url(url) is False

    def test_rejects_non_string(self) -> None:
        assert is_valid_git_url(None) is False  # type: ignore[arg-type]


class TestClonedRepo:
    """Context-manager-driven shallow clone."""

    def test_invalid_url_raises_immediately(self) -> None:
        with pytest.raises(GitCloneError, match="Not a recognized git URL"):
            with cloned_repo("not-a-url"):
                pass

    def test_git_missing_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("scanner.git_source.shutil.which", lambda _: None)
        with pytest.raises(GitCloneError, match="git is not installed"):
            with cloned_repo("https://github.com/owner/repo"):
                pass

    def test_clone_failure_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("scanner.git_source.shutil.which", lambda _: "/usr/bin/git")

        def fake_run(*args, **kwargs):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=args[0],
                stderr="fatal: repository not found",
            )

        monkeypatch.setattr("scanner.git_source.subprocess.run", fake_run)

        with pytest.raises(GitCloneError, match="git clone failed"):
            with cloned_repo("https://github.com/owner/missing-repo"):
                pass

    def test_successful_clone_yields_result_and_cleans_up(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("scanner.git_source.shutil.which", lambda _: "/usr/bin/git")
        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            if cmd[1] == "clone":
                target = Path(cmd[-1])
                target.mkdir(parents=True, exist_ok=True)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return subprocess.CompletedProcess(cmd, 0, "abc1234deadbeef\n", "")

        monkeypatch.setattr("scanner.git_source.subprocess.run", fake_run)

        recorded_path: Path | None = None
        with cloned_repo("https://github.com/owner/repo") as result:
            recorded_path = result.repo_path
            assert result.url == "https://github.com/owner/repo"
            assert result.head_sha == "abc1234deadbeef"
            assert recorded_path.exists()

        assert recorded_path is not None
        assert not recorded_path.exists()

    def test_clone_invocation_uses_shell_false_and_shallow_depth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("scanner.git_source.shutil.which", lambda _: "/usr/bin/git")
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            if cmd[1] == "clone":
                captured["clone_cmd"] = list(cmd)
                captured["clone_kwargs"] = kwargs
                Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr("scanner.git_source.subprocess.run", fake_run)

        with cloned_repo("https://github.com/owner/repo"):
            pass

        clone_cmd = captured["clone_cmd"]
        clone_kwargs = captured["clone_kwargs"]
        assert isinstance(clone_cmd, list)
        assert clone_cmd[0] == "git"
        assert "clone" in clone_cmd
        assert "--depth" in clone_cmd
        depth_index = clone_cmd.index("--depth")
        assert clone_cmd[depth_index + 1] == "1"
        assert isinstance(clone_kwargs, dict)
        assert clone_kwargs.get("shell") is False
        assert clone_kwargs.get("check") is True

    def test_head_sha_is_none_when_rev_parse_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("scanner.git_source.shutil.which", lambda _: "/usr/bin/git")

        def fake_run(cmd, **kwargs):
            if cmd[1] == "clone":
                Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

        monkeypatch.setattr("scanner.git_source.subprocess.run", fake_run)

        with cloned_repo("https://github.com/owner/repo") as result:
            assert result.head_sha is None
