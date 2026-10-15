"""学习者进度：记录哪些节点已经完成。

进度存放在用户目录（``~/.agtstu/progress.json``），而不是项目目录里——
这样升级或重新克隆项目时进度不会丢，也不会被误提交进 Git。
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["progress_file", "load", "save", "mark", "unmark", "clear"]


def progress_file() -> Path:
    """进度文件的完整路径。"""
    return Path.home() / ".agtstu" / "progress.json"


def load() -> set[str]:
    """读取已完成的节点 id 集合。文件不存在时返回空集合。"""
    path = progress_file()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # 进度文件损坏不应导致程序无法运行，退回空进度并提示
        print(f"[警告] 进度文件无法解析，已按空进度处理：{path}")
        return set()
    done = data.get("done", [])
    return {str(x) for x in done} if isinstance(done, list) else set()


def save(done: set[str]) -> Path:
    """写回进度文件，返回写入路径。"""
    path = progress_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"done": sorted(done)}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def mark(node_id: str) -> set[str]:
    """把某节点标记为已完成。"""
    done = load()
    done.add(node_id)
    save(done)
    return done


def unmark(node_id: str) -> set[str]:
    """取消某节点的完成标记。"""
    done = load()
    done.discard(node_id)
    save(done)
    return done


def clear() -> None:
    """清空全部进度。"""
    save(set())
