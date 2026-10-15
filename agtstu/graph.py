"""依赖图引擎（内核 A）。

这是整个项目的计算核心。它把学习路径当作一张**有向无环图**来处理，
而不是一份线性清单。四个能力对应四类算法：

======================  ==========================================
能力                    算法
======================  ==========================================
校验内容                悬空引用扫描 + 孤立节点扫描 + DFS 三色环检测
算「现在能学什么」       拓扑前沿（入度归零的节点）
算「达成目标还差什么」    祖先集合 + 拓扑排序
列出正确学习顺序          Kahn 拓扑排序
======================  ==========================================

为什么需要它
------------
内容会长期增长到几百个节点。到那个规模，手工维护「谁依赖谁」必然出错——
写错一个前置就会让某个节点永远解锁不了。**这是程序该干的活。**
"""

from __future__ import annotations

from collections.abc import Iterable

from .model import Node

__all__ = [
    "build_index",
    "find_cycles",
    "topological_order",
    "validate",
    "unlocked",
    "blocked",
    "plan",
    "completion",
    "stage_summary",
]


def build_index(nodes: Iterable[Node]) -> dict[str, Node]:
    """把节点列表转成 ``{id: Node}`` 的索引。"""
    return {n.id: n for n in nodes}


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def find_cycles(nodes: Iterable[Node]) -> list[list[str]]:
    """找出所有循环依赖，返回若干个环路（每个是 id 列表，首尾相同）。

    用 DFS 三色标记：白色=未访问，灰色=正在访问，黑色=已完成。
    当从当前节点走到一个**灰色**节点时，说明走回了自己所在的路径——即成环。

    这是本项目最有价值的一项校验：环会让被卷入的节点**永远无法解锁**，
    而只在纸上画路线图时几乎不可能发现。
    """
    node_list = list(nodes)
    index = build_index(node_list)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n.id: WHITE for n in node_list}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(nid: str) -> None:
        color[nid] = GRAY
        stack.append(nid)
        for dep in index[nid].requires:
            if dep not in index:
                continue                      # 悬空引用交给 validate 报告
            if color[dep] == WHITE:
                visit(dep)
            elif color[dep] == GRAY:
                start = stack.index(dep)
                cycles.append(stack[start:] + [dep])
        stack.pop()
        color[nid] = BLACK

    for node in node_list:
        if color[node.id] == WHITE:
            visit(node.id)

    return cycles


def validate(nodes: Iterable[Node]) -> list[str]:
    """校验路径数据的完整性，返回问题描述列表；空列表表示没问题。

    检查四类问题：

    1. **自依赖** —— 节点的 ``requires`` 里写了自己的 id
    2. **悬空引用** —— ``requires`` 指向了不存在的节点
    3. **孤立节点** —— 既没有前置、也没被任何节点依赖（通常是漏写）
    4. **循环依赖** —— 见 :func:`find_cycles`
    """
    node_list = list(nodes)
    index = build_index(node_list)
    issues: list[str] = []

    for node in node_list:
        for dep in node.requires:
            if dep == node.id:
                issues.append(f"节点 {node.id!r} 依赖了它自己")
            elif dep not in index:
                issues.append(
                    f"节点 {node.id!r} 的前置 {dep!r} 不存在"
                )

    if len(node_list) > 1:
        referenced = {d for n in node_list for d in n.requires}
        for node in node_list:
            if node.is_entry and node.id not in referenced:
                issues.append(
                    f"节点 {node.id!r} 既没有前置、也没被任何节点依赖，"
                    "可能是漏写了依赖关系"
                )

    for cycle in find_cycles(node_list):
        issues.append("检测到循环依赖：" + " → ".join(cycle))

    return issues


# ---------------------------------------------------------------------------
# 排序与求解
# ---------------------------------------------------------------------------

def topological_order(nodes: Iterable[Node]) -> list[str]:
    """返回一个满足所有前置关系的学习顺序（Kahn 算法）。

    同一层内按**文件中的书写顺序**排列，保证结果稳定可复现。

    若数据中存在环，被环卡住的节点不会出现在结果里——此时应先用
    :func:`validate` 修数据。
    """
    node_list = list(nodes)
    index = build_index(node_list)

    # 入度 = 尚未满足的前置数量
    indegree = {
        n.id: sum(1 for d in n.requires if d in index) for n in node_list
    }
    # 后继表：完成某节点后，谁的前置少了一个
    successors: dict[str, list[str]] = {n.id: [] for n in node_list}
    for node in node_list:
        for dep in node.requires:
            if dep in index:
                successors[dep].append(node.id)

    file_order = {n.id: i for i, n in enumerate(node_list)}
    ready = sorted(
        (nid for nid, deg in indegree.items() if deg == 0),
        key=file_order.__getitem__,
    )

    result: list[str] = []
    while ready:
        nid = ready.pop(0)
        result.append(nid)
        for nxt in successors[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort(key=file_order.__getitem__)

    return result


def unlocked(nodes: Iterable[Node], done: Iterable[str] = ()) -> list[str]:
    """返回**现在就可以学**的节点 id（前置已全部完成）。

    这就是拓扑前沿。它不是「下一个」——满足条件的往往有多个，
    具体先学哪个由学习者按目标自己判断。
    """
    done_set = set(done)
    return [
        n.id for n in nodes
        if n.id not in done_set and all(d in done_set for d in n.requires)
    ]


def blocked(
    nodes: Iterable[Node], done: Iterable[str] = ()
) -> dict[str, list[str]]:
    """返回**尚未解锁**的节点，以及它们各自还缺哪些前置。

    返回
    ----
    dict
        ``{节点 id: [缺失的前置 id, ...]}``
    """
    done_set = set(done)
    result: dict[str, list[str]] = {}
    for node in nodes:
        if node.id in done_set:
            continue
        missing = [d for d in node.requires if d not in done_set]
        if missing:
            result[node.id] = missing
    return result


def plan(
    nodes: Iterable[Node], target: str, done: Iterable[str] = ()
) -> list[str]:
    """给出「从当前位置达成 ``target`` 还需要按什么顺序学哪些节点」。

    做法：先收集 target 的全部祖先（含自身），去掉已完成的，
    再按拓扑序排列。

    异常
    ----
    KeyError
        目标节点不存在。
    """
    node_list = list(nodes)
    index = build_index(node_list)
    if target not in index:
        raise KeyError(f"路径中没有节点 {target!r}")

    done_set = set(done)

    # 收集祖先：从 target 出发沿 requires 反向遍历
    needed: set[str] = set()
    stack = [target]
    while stack:
        nid = stack.pop()
        if nid in needed:
            continue
        needed.add(nid)
        stack.extend(index[nid].requires)

    todo = needed - done_set
    return [nid for nid in topological_order(node_list) if nid in todo]


# ---------------------------------------------------------------------------
# 进度统计
# ---------------------------------------------------------------------------

def completion(nodes: Iterable[Node], done: Iterable[str] = ()) -> float:
    """完成度，0.0 ~ 1.0。已完成集合里不属于路径的 id 会被忽略。"""
    node_list = list(nodes)
    if not node_list:
        return 0.0
    valid = {n.id for n in node_list}
    return len(valid & set(done)) / len(valid)


def stage_summary(
    nodes: Iterable[Node], done: Iterable[str] = ()
) -> list[tuple[str, int, int]]:
    """按阶段汇总进度。

    返回
    ----
    list[tuple]
        每项为 ``(阶段名, 已完成数, 总数)``，按文件中首次出现的顺序排列。
    """
    node_list = list(nodes)
    done_set = set(done)

    stages: dict[str, list[str]] = {}
    for node in node_list:
        stages.setdefault(node.stage or "未分组", []).append(node.id)

    return [
        (name, sum(1 for nid in ids if nid in done_set), len(ids))
        for name, ids in stages.items()
    ]
