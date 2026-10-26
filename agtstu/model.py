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

两层内容结构
------------
一个节点下面是**知识点**（:class:`Topic`），每个知识点可以带「怎么用」的
示例代码；节点级则挂**真实的坑**（:class:`Pitfall`）。

``skills`` 与 ``pitfalls`` 都支持**简单写法**（纯字符串）和**详细写法**
（字典），加载时统一解析成对象。这样既兼容早期数据，也允许逐条补细节。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Node", "Project", "Resource", "Topic", "Pitfall", "from_dict"]

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
class Topic:
    """一个知识点，可以带「怎么用」的示例。

    简单写法只写标题；详细写法补上说明、示例代码与运行结果。
    """

    id: str = ""
    """节点内唯一标识，供页面定位。省略时按序号生成。"""

    title: str = ""
    """知识点名称。"""

    what: str = ""
    """这是什么、解决什么问题。一两句话讲清。"""

    example: str = ""
    """用法示例代码。应当可以直接运行。"""

    output: str = ""
    """示例代码的运行结果。留空表示无输出。"""

    note: str = ""
    """补充说明：边界情况、常见误用、和相邻概念的区别。"""

    @property
    def has_example(self) -> bool:
        return bool(self.example.strip())


@dataclass
class Pitfall:
    """一条真实的坑。

    纯文本写法时 ``text`` 承载全部内容，页面按普通段落展示；
    详细写法下四个字段分开，页面按「报错 → 为什么 → 怎么修」呈现。

    **为什么这么设计**：一条坑真正有价值的部分不是"要注意 X"这种劝告，
    而是「什么报错 + 为什么会这样 + 具体怎么改」。
    有了报错原文，学习者才能拿去搜索自救。
    """

    text: str = ""
    """兼容纯文本写法时的完整描述。"""

    symptom: str = ""
    """症状：报错原文，或能被观察到的现象。"""

    scene: str = ""
    """触发场景：什么样的代码会踩到。"""

    why: str = ""
    """原因：为什么会这样。"""

    fix: str = ""
    """解法：具体怎么改。"""

    search: str = ""
    """建议搜索词——教学习者怎么自己查。"""

    @property
    def structured(self) -> bool:
        """是否为详细写法。"""
        return bool(self.symptom or self.scene or self.why or self.fix)


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

    summary: str = ""
    """一句话说明这个节点解决什么问题。"""

    skills: list[Topic] = field(default_factory=list)
    """知识点清单。有序——按学习顺序排列。"""

    acceptance: list[str] = field(default_factory=list)
    """验收标准。逐条自评，全部通过即视为合格——不设标准答案。"""

    project: Project | None = None
    """配套的参考项目。"""

    pitfalls: list[Pitfall] = field(default_factory=list)
    """真实的坑。这是本项目区别于普通资料的核心。"""

    resources: list[Resource] = field(default_factory=list)
    """延伸资源链接。"""

    @property
    def is_entry(self) -> bool:
        """是否为入口节点（没有任何前置）。"""
        return not self.requires

    @property
    def topic_titles(self) -> list[str]:
        """知识点标题列表，供命令行快速显示。"""
        return [t.title for t in self.skills]

    def summary_line(self) -> str:
        """单行摘要，用于列表展示。"""
        parts = [self.title]
        if self.skills:
            parts.append(f"{len(self.skills)} 个知识点")
        if self.acceptance:
            parts.append(f"{len(self.acceptance)} 条验收")
        return "  ·  ".join(parts)


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

def _parse_topics(raw: Any, node_id: str) -> list[Topic]:
    """知识点支持两种写法：纯字符串，或带 example 的字典。"""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"节点 {node_id!r} 的 skills 应为列表。")

    topics: list[Topic] = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            topics.append(Topic(id=f"t{i + 1}", title=item))
        elif isinstance(item, dict):
            title = item.get("title") or item.get("name") or ""
            if not title:
                raise ValueError(
                    f"节点 {node_id!r} 的第 {i + 1} 个知识点缺少 title。"
                )
            topics.append(Topic(
                id=str(item.get("id") or f"t{i + 1}"),
                title=str(title),
                what=str(item.get("what", "")),
                example=str(item.get("example", "")),
                output=str(item.get("output", "")),
                note=str(item.get("note", "")),
            ))
        else:
            raise ValueError(
                f"节点 {node_id!r} 的第 {i + 1} 个知识点类型不对，"
                "应为字符串或字典。"
            )
    return topics


def _parse_pitfalls(raw: Any, node_id: str) -> list[Pitfall]:
    """坑支持两种写法：纯字符串，或带 symptom/why/fix 的字典。"""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"节点 {node_id!r} 的 pitfalls 应为列表。")

    result: list[Pitfall] = []
    for item in raw:
        if isinstance(item, str):
            result.append(Pitfall(text=item))
        elif isinstance(item, dict):
            result.append(Pitfall(
                text=str(item.get("text", "")),
                symptom=str(item.get("symptom", "")),
                scene=str(item.get("scene", "")),
                why=str(item.get("why", "")),
                fix=str(item.get("fix", "")),
                search=str(item.get("search", "")),
            ))
        else:
            raise ValueError(f"节点 {node_id!r} 的坑类型不对，应为字符串或字典。")
    return result


def from_dict(raw: dict[str, Any], *, source: str = "") -> Node:
    """把 YAML 解析出的字典转成 :class:`Node`。

    参数
    ----
    raw : dict
        原始字典。
    source : str
        来源标识（通常是文件路径），用于报错时定位。

    异常
    -----
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

    node_id = str(raw["id"])

    requires = raw.get("requires") or []
    if isinstance(requires, str):
        # 允许写 `requires: py_env` 这种单个前置的简写
        requires = [requires]
    if not isinstance(requires, list):
        raise ValueError(f"节点 {node_id!r} 的 requires 应为列表{where}。")

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
        id=node_id,
        title=str(raw["title"]),
        requires=[str(x) for x in requires],
        stage=str(raw.get("stage", "")),
        summary=str(raw.get("summary", "")),
        skills=_parse_topics(raw.get("skills"), node_id),
        acceptance=[str(x) for x in (raw.get("acceptance") or [])],
        project=project,
        pitfalls=_parse_pitfalls(raw.get("pitfalls"), node_id),
        resources=resources,
    )
