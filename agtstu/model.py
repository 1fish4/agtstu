"""数据模型：学习路径中的一个「节点」。

一个节点 = 一个可以独立完成、独立验收的学习单元。
它既是**内容的书写格式**，也是**引擎的计算对象**——两者共用这一份定义。

设计要点
--------
节点的 ``requires`` 字段就是图的**边**。整条学习路径因此构成一张
有向无环图（DAG）：一个节点可以有多个前置，也能解锁多个后继。

    py_basic ──┬─> py_container ──┐
               │                  ├─> py_func ──> py_module
               └─> py_flow ───────┘

这份定义写在一个 YAML 文件里，见 ``data/path.yaml``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Node", "Project", "Resource", "from_dict"]

#: 必填字段。缺任何一个都会在加载阶段报错。
REQUIRED_FIELDS = ("id", "title", "requires")


@dataclass
class Project:
    """参考项目。项目本身可以是自己做的，也可以指向他人的开源仓库。"""

    name: str
    note: str = ""
    repo: str = ""

    @property
    def is_external(self) -> bool:
        """是否指向他人仓库（用于提示版权注意事项）。"""
        return bool(self.repo)


@dataclass
class Resource:
    """一条学习资源。只放链接，不转载内容。"""

    title: str
    url: str
    note: str = ""


@dataclass
class Node:
    """学习路径中的一个节点。"""

    id: str
    """英文唯一标识，用于建立依赖关系。"""

    title: str
    """中文显示名。"""

    requires: list[str] = field(default_factory=list)
    """前置节点 id 列表——这就是图中的边。"""

    stage: str = ""
    """所属阶段，用于分组展示。"""

    skills: list[str] = field(default_factory=list)
    """本节点要掌握的知识点清单。"""

    acceptance: list[str] = field(default_factory=list)
    """验收标准。逐条自评，全部通过即视为合格——不设标准答案。"""

    project: Project | None = None
    """配套的参考项目。"""

    pitfalls: list[str] = field(default_factory=list)
    """常见坑。这是本项目区别于普通资料的核心——作者真实踩过的记录。"""

    resources: list[Resource] = field(default_factory=list)
    """延伸资源链接。"""

    @property
    def is_entry(self) -> bool:
        """是否为入口节点（没有任何前置）。"""
        return not self.requires

    def summary(self) -> str:
        """单行摘要，用于列表展示。"""
        parts = [f"{self.title}"]
        if self.skills:
            parts.append(f"{len(self.skills)} 个知识点")
        if self.acceptance:
            parts.append(f"{len(self.acceptance)} 条验收")
        return "  ·  ".join(parts)


def from_dict(raw: dict[str, Any], *, source: str = "") -> Node:
    """把 YAML 解析出的字典转成 :class:`Node`。

    参数
    ----
    raw : dict
        原始字典。
    source : str
        来源标识（通常是文件路径），用于报错时定位。

    异常
    ----
    ValueError
        缺少必填字段，或字段类型不对。
    """
    where = f"（来自 {source}）" if source else ""

    missing = [f for f in REQUIRED_FIELDS if f not in raw or raw[f] in (None, "")]
    if missing:
        raise ValueError(
            f"节点缺少必填字段 {missing}{where}。"
            f"必填项为 {list(REQUIRED_FIELDS)}。"
        )

    requires = raw.get("requires") or []
    if isinstance(requires, str):
        # 允许写 `requires: py_env` 这种单个前置的简写
        requires = [requires]
    if not isinstance(requires, list):
        raise ValueError(f"节点 {raw['id']!r} 的 requires 应为列表{where}。")

    project = None
    raw_project = raw.get("project")
    if raw_project:
        if isinstance(raw_project, str):
            project = Project(name=raw_project)
        else:
            project = Project(
                name=raw_project.get("name", ""),
                note=raw_project.get("note", ""),
                repo=raw_project.get("repo", ""),
            )

    resources = [
        Resource(
            title=r.get("title", ""),
            url=r.get("url", ""),
            note=r.get("note", ""),
        )
        for r in (raw.get("resources") or [])
    ]

    return Node(
        id=str(raw["id"]),
        title=str(raw["title"]),
        requires=[str(x) for x in requires],
        stage=str(raw.get("stage", "")),
        skills=[str(x) for x in (raw.get("skills") or [])],
        acceptance=[str(x) for x in (raw.get("acceptance") or [])],
        project=project,
        pitfalls=[str(x) for x in (raw.get("pitfalls") or [])],
        resources=resources,
    )
