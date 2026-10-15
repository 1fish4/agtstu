"""加载器：把 YAML 内容文件读成 :class:`Node` 集合。

内容与代码分离是本项目的原则：路径数据在 ``data/path.yaml``，
引擎代码在本包里。改内容不需要动代码。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .model import Node, from_dict

__all__ = ["load_nodes", "default_data_file", "DEFAULT_DATA"]

#: 包内自带的路径数据
DEFAULT_DATA = Path(__file__).parent / "data" / "path.yaml"


def default_data_file() -> Path:
    """返回包内默认的路径数据文件。"""
    return DEFAULT_DATA


def load_nodes(path: str | Path | None = None) -> list[Node]:
    """从 YAML 文件加载节点列表。

    参数
    ----
    path : str 或 Path, 可选
        数据文件路径。省略时使用包内自带的 ``data/path.yaml``。

    返回
    ----
    list[Node]
        按文件中出现的顺序返回。

    异常
    -----
    FileNotFoundError
        文件不存在。
    ValueError
        文件结构不对，或某个节点字段缺失。
    """
    p = Path(path) if path is not None else DEFAULT_DATA
    if not p.is_file():
        raise FileNotFoundError(f"找不到路径数据文件：{p}")

    with p.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict) or "nodes" not in raw:
        raise ValueError(
            f"{p} 的结构应为 {{'nodes': [...]}}，"
            f"实际读到 {type(raw).__name__}。"
        )

    entries = raw["nodes"]
    if not isinstance(entries, list):
        raise ValueError(f"{p} 的 nodes 字段应为列表。")

    nodes = [from_dict(item, source=f"{p.name}#{i}") for i, item in enumerate(entries)]

    seen: set[str] = set()
    for node in nodes:
        if node.id in seen:
            raise ValueError(f"节点 id 重复：{node.id!r}")
        seen.add(node.id)

    return nodes
