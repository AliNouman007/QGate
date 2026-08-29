from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from zipfile import ZipFile

if TYPE_CHECKING:
    from collections.abc import Iterator


class ProjectSource(Protocol):
    @property
    def root(self) -> Path: ...

    @property
    def source_id(self) -> str: ...

    def iter_files(self) -> Iterator[Path]: ...


class LocalPathSource:
    def __init__(self, root: str | Path) -> None:
        path = Path(root).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Project path is not a directory: {path}")
        self._root = path

    @property
    def root(self) -> Path:
        return self._root

    @property
    def source_id(self) -> str:
        return f"local:{self._root.as_posix()}"

    def iter_files(self) -> Iterator[Path]:
        for path in self._root.rglob("*"):
            if path.is_file():
                yield path


class ZipProjectSource:
    def __init__(self, archive: str | Path) -> None:
        path = Path(archive).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise ValueError(f"Project archive does not exist: {path}")
        self._archive = path
        self._temp_dir: Path | None = None

    def __enter__(self) -> ZipProjectSource:
        temp_dir = Path(tempfile.mkdtemp(prefix="qgate-project-"))
        with ZipFile(self._archive) as archive:
            root = temp_dir.resolve()
            for member in archive.infolist():
                target = (temp_dir / member.filename).resolve()
                if root not in target.parents and target != root:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    raise ValueError("ZIP contains a path outside its extraction directory")
            archive.extractall(temp_dir)
        self._temp_dir = temp_dir
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    @property
    def root(self) -> Path:
        if self._temp_dir is None:
            raise RuntimeError("ZipProjectSource must be used as a context manager")
        return self._temp_dir

    @property
    def source_id(self) -> str:
        return f"zip:{self._archive.as_posix()}"

    def iter_files(self) -> Iterator[Path]:
        for path in self.root.rglob("*"):
            if path.is_file():
                yield path

    def close(self) -> None:
        if self._temp_dir is not None:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None
