"""Atomic writes for pipeline artifacts."""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile


def save_bytes(path: Path, data: bytes) -> None:
    """Replace a file only after its complete contents reach disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)


def save_json(path: Path, value: dict) -> None:
    """Write a portable UTF-8 checkpoint."""
    save_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())
