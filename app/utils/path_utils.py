"""
文件路径解析工具

负责把模型或工具返回的虚拟路径、上传文件路径和相对路径统一转换为本地绝对路径
后续文件读取、Markdown 生成和 PDF 转换工具都可以复用这里的解析规则
"""

import os
from pathlib import Path
from typing import Optional


def resolve_path(filename: str, session_dir: Optional[str] = None) -> str:
    """
    解析文件路径，并尽量把任务产物限制在当前会话目录中

    :param filename: 模型、工具或用户传入的文件名/路径
    :param session_dir: 当前任务的会话目录
    :return: 解析后的绝对路径
    """
    path = Path(filename)
    path_str = filename.replace("\\", "/")

    # 在任何兼容路径转换前拒绝父目录跳转，避免后续前缀修正掩盖越界输入。
    if ".." in Path(path_str).parts:
        raise ValueError("不允许使用父目录路径")

    # 大模型常返回 /workspace、/mnt/data 这类沙箱路径，本地项目需要先剥离虚拟前缀
    for prefix in ["/workspace", "/mnt/data", "/home/user"]:
        if path_str.startswith(prefix):
            cleaned = path_str[len(prefix) :].lstrip("/")
            path = Path(cleaned)
            path_str = str(path).replace("\\", "/")
            break

    # 工具只能通过会话工作副本读取附件，不能绕过边界直接访问上传暂存目录。
    if "updated" in Path(path_str).parts:
        raise ValueError("不允许访问上传暂存路径")

    if not session_dir:
        return str(path.resolve())

    session_path = Path(session_dir).resolve()
    session_name = session_path.name
    is_unix_abs = path_str.startswith("/")

    if path.is_absolute() or (os.name == "nt" and is_unix_abs):
        # Windows 下 "/xxx" 没有盘符，按会话目录内的相对路径处理
        if os.name == "nt" and is_unix_abs and not path.drive:
            full_path = session_path / path_str.lstrip("/")
        else:
            full_path = path.resolve()

        try:
            if session_path in full_path.parents or full_path == session_path:
                return _fix_nested_session_path(full_path, session_path, session_name)
        except Exception:
            pass

        raise ValueError("不允许访问当前会话目录之外的文件")

    parts = path.parts

    # 避免模型把 session 名或 output 前缀重复拼到当前会话目录里
    if session_name in parts:
        index = parts.index(session_name)
        path = Path(*parts[index + 1 :])

    elif parts and parts[0] == "output":
        path = Path(*parts[1:])

    target_path = (session_path / path).resolve()
    if not target_path.is_relative_to(session_path):
        raise ValueError("不允许访问当前会话目录之外的文件")
    return str(target_path)


def _fix_nested_session_path(
    full_path: Path,
    session_path: Path,
    session_name: str,
) -> str:
    """
    修正 session_xxx/session_xxx/file.md 这类重复嵌套路径
    """
    parts = full_path.parts
    for index in range(len(parts) - 1):
        if parts[index] == session_name and parts[index + 1] == session_name:
            relative_path = Path(*parts[index + 2 :])
            target_path = (session_path / relative_path).resolve()
            break
    else:
        target_path = full_path.resolve()

    if not target_path.is_relative_to(session_path):
        raise ValueError("不允许访问当前会话目录之外的文件")
    return str(target_path)
