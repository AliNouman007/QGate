from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from .diff_parser import parse_unified_diff
from .models import ChangeSet, ChangeSourceKind


class ChangeSource(Protocol):
    def load(self) -> ChangeSet: ...


class UnifiedDiffSource:
    def __init__(
        self,
        text: str,
        *,
        source_id: str = "patch",
        source_kind: ChangeSourceKind = ChangeSourceKind.UNIFIED_DIFF,
        base_ref: str | None = None,
        head_ref: str | None = None,
        title: str | None = None,
        url: str | None = None,
    ) -> None:
        self.text = text
        self.source_id = source_id
        self.source_kind = source_kind
        self.base_ref = base_ref
        self.head_ref = head_ref
        self.title = title
        self.url = url

    @classmethod
    def from_file(cls, path: str | Path) -> UnifiedDiffSource:
        patch = Path(path).expanduser().resolve()
        if not patch.exists() or not patch.is_file():
            raise ValueError(f"Diff/patch file does not exist: {patch}")
        return cls(patch.read_text(encoding="utf-8"), source_id=f"patch:{patch.as_posix()}")

    def load(self) -> ChangeSet:
        return parse_unified_diff(
            self.text,
            source_kind=self.source_kind,
            source_id=self.source_id,
            base_ref=self.base_ref,
            head_ref=self.head_ref,
            title=self.title,
            url=self.url,
        )


class GitHubPatchSource(UnifiedDiffSource):
    """Transport-neutral GitHub adapter for patch text already fetched by a connector."""

    def __init__(
        self,
        text: str,
        *,
        repository: str,
        pr_number: int,
        base_ref: str | None = None,
        head_ref: str | None = None,
        title: str | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(
            text,
            source_id=f"github:{repository}#pr-{pr_number}",
            source_kind=ChangeSourceKind.GITHUB_PR,
            base_ref=base_ref,
            head_ref=head_ref,
            title=title,
            url=url,
        )


class LocalGitSource:
    def __init__(
        self,
        repo_path: str | Path,
        *,
        base_ref: str = "main",
        head_ref: str = "HEAD",
    ) -> None:
        path = Path(repo_path).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Git repository path is not a directory: {path}")
        self.repo_path = path
        self.base_ref = base_ref
        self.head_ref = head_ref

    def load(self) -> ChangeSet:
        self._run("rev-parse", "--is-inside-work-tree")
        self._run("rev-parse", "--verify", self.base_ref)
        self._run("rev-parse", "--verify", self.head_ref)
        patch = self._run(
            "diff",
            "--no-ext-diff",
            "--find-renames",
            "--unified=3",
            f"{self.base_ref}...{self.head_ref}",
        )
        return parse_unified_diff(
            patch,
            source_kind=ChangeSourceKind.LOCAL_GIT,
            source_id=f"git:{self.repo_path.as_posix()}:{self.base_ref}...{self.head_ref}",
            base_ref=self.base_ref,
            head_ref=self.head_ref,
        )

    def _run(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            stderr = getattr(exc, "stderr", "") or ""
            raise ValueError(
                f"Git command failed for {self.repo_path}: {' '.join(args)} {stderr.strip()}"
            ) from exc
        return result.stdout
