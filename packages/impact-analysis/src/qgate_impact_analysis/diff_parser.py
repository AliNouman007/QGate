from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    ChangedFile,
    ChangedLineRange,
    ChangeGap,
    ChangeSet,
    ChangeSourceKind,
    DiffHunk,
    FileChangeStatus,
)

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


@dataclass
class _FileBuilder:
    old_path: str | None
    new_path: str | None
    status: FileChangeStatus = FileChangeStatus.MODIFIED
    hunks: list[DiffHunk] | None = None
    additions: int = 0
    deletions: int = 0

    def __post_init__(self) -> None:
        if self.hunks is None:
            self.hunks = []


def parse_unified_diff(
    text: str,
    *,
    source_kind: ChangeSourceKind = ChangeSourceKind.UNIFIED_DIFF,
    source_id: str = "patch",
    base_ref: str | None = None,
    head_ref: str | None = None,
    title: str | None = None,
    url: str | None = None,
) -> ChangeSet:
    lines = text.splitlines()
    files: list[ChangedFile] = []
    gaps: list[ChangeGap] = []
    current: _FileBuilder | None = None
    index = 0

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        path = current.new_path or current.old_path
        if path is not None:
            files.append(
                ChangedFile(
                    path=_clean_path(path),
                    old_path=_clean_path(current.old_path) if current.old_path else None,
                    status=current.status,
                    hunks=current.hunks or [],
                    additions=current.additions,
                    deletions=current.deletions,
                )
            )
        current = None

    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git "):
            flush()
            parts = line.split()
            if len(parts) >= 4:
                current = _FileBuilder(parts[2], parts[3])
            else:
                gaps.append(ChangeGap(reason="malformed_diff_header", detail=line[:240]))
            index += 1
            continue

        if current is None:
            index += 1
            continue

        if line.startswith("new file mode "):
            current.status = FileChangeStatus.ADDED
        elif line.startswith("deleted file mode "):
            current.status = FileChangeStatus.DELETED
        elif line.startswith("rename from "):
            current.status = FileChangeStatus.RENAMED
            current.old_path = line.removeprefix("rename from ")
        elif line.startswith("rename to "):
            current.status = FileChangeStatus.RENAMED
            current.new_path = line.removeprefix("rename to ")
        elif line.startswith("--- "):
            old_path = line.removeprefix("--- ")
            if old_path != "/dev/null":
                current.old_path = old_path
        elif line.startswith("+++ "):
            new_path = line.removeprefix("+++ ")
            if new_path != "/dev/null":
                current.new_path = new_path
        elif line.startswith("@@ "):
            match = _HUNK_RE.match(line)
            if match is None:
                gaps.append(ChangeGap(path=_clean_path(current.new_path or current.old_path or ""), reason="unsupported_hunk", detail=line[:240]))
                index += 1
                continue
            old_start = int(match.group(1))
            old_count = int(match.group(2) or "1")
            new_start = int(match.group(3))
            new_count = int(match.group(4) or "1")
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@ ", "diff --git ")):
                hunk_line = lines[index]
                body.append(hunk_line)
                if hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                    current.additions += 1
                elif hunk_line.startswith("-") and not hunk_line.startswith("---"):
                    current.deletions += 1
                index += 1
            assert current.hunks is not None
            current.hunks.append(
                DiffHunk(
                    old_range=ChangedLineRange(start=old_start, count=old_count),
                    new_range=ChangedLineRange(start=new_start, count=new_count),
                    header=line,
                    excerpt="\n".join(body[:80])[:8000],
                )
            )
            continue
        index += 1

    flush()
    return ChangeSet(
        source_kind=source_kind,
        source_id=source_id,
        base_ref=base_ref,
        head_ref=head_ref,
        title=title,
        url=url,
        files=files,
        gaps=gaps,
    )


def _clean_path(path: str) -> str:
    value = path.strip()
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value
