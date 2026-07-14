"""File storage operations for uploaded documents."""

import os
import shutil
from pathlib import Path
from typing import List

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv", ".rst", ".html"}


def _get_data_dir() -> Path:
    from app.config import DATA_DIR
    return Path(DATA_DIR).resolve()


def ensure_task_dir(task_id: str) -> Path:
    task_dir = _get_data_dir() / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def save_uploaded_file(task_id: str, filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    docs_dir = ensure_task_dir(task_id) / "documents"
    docs_dir.mkdir(exist_ok=True)

    dest = docs_dir / filename
    counter = 1
    while dest.exists():
        stem = Path(filename).stem
        dest = docs_dir / f"{stem}_{counter}{ext}"
        counter += 1

    dest.write_bytes(content)
    return dest.as_posix()


def get_document_paths(task_id: str) -> List[str]:
    docs_dir = ensure_task_dir(task_id) / "documents"
    if not docs_dir.exists():
        return []
    # Use forward slashes to avoid Windows backslash escape issues
    return sorted(p.as_posix() for p in docs_dir.iterdir() if p.is_file())


def delete_task_data(task_id: str) -> None:
    task_dir = _get_data_dir() / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
