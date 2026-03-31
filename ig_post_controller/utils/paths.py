from __future__ import annotations

import os
from pathlib import Path


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def open_in_file_browser(path: str | Path) -> None:
    os.startfile(str(path))
