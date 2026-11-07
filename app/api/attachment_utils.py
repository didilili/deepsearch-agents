"""上传附件的路径校验与安全删除逻辑。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RemovalResult:
    filename: str
    work_copy: str


def validate_path_component(value: str, label: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or not all(char.isascii() and (char.isalnum() or char in "-_.") for char in value)
    ):
        raise ValueError(f"无效的{label}")
    return value


def session_directory(root: Path, thread_id: str) -> Path:
    thread_id = validate_path_component(thread_id, "会话编号")
    resolved_root = root.resolve()
    target = (resolved_root / f"session_{thread_id}").resolve()
    if not target.is_relative_to(resolved_root):
        raise ValueError("会话目录超出允许范围")
    return target


def validate_filename(filename: str) -> str:
    if (
        not filename
        or filename in {".", ".."}
        or any(character in filename for character in "/\\:\0")
    ):
        raise ValueError("无效的文件名")
    return filename


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_attachment(
    upload_root: Path,
    output_root: Path,
    thread_id: str,
    filename: str,
) -> RemovalResult:
    filename = validate_filename(filename)
    upload_dir = session_directory(upload_root, thread_id)
    output_dir = session_directory(output_root, thread_id)
    staged_file = (upload_dir / filename).resolve()
    work_file = (output_dir / filename).resolve()

    if not staged_file.is_relative_to(upload_dir) or not work_file.is_relative_to(output_dir):
        raise ValueError("附件路径超出允许范围")
    if not staged_file.is_file():
        raise FileNotFoundError("上传附件不存在")

    work_copy = "not_found"
    if work_file.exists():
        if not work_file.is_file():
            raise IsADirectoryError("同名工作路径不是普通文件")
        if file_digest(staged_file) == file_digest(work_file):
            work_file.unlink()
            work_copy = "removed"
        else:
            work_copy = "kept_modified"

    staged_file.unlink()
    return RemovalResult(filename=filename, work_copy=work_copy)
