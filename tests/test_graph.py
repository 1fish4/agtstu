"""依赖图引擎的单元测试。

分两部分：
* **对真实数据的测试** —— 校验包内自带的 path.yaml 本身没有问题
* **对合成数据的测试** —— 用构造出来的小图验证算法正确性
"""

from __future__ import annotations

import pytest

from agtstu import graph
from agtstu.loader import load_nodes
from agtstu.model import Node


def make(nid: str, requires: list[str] | None = None, **kw) -> Node:
    """快速构造一个测试节点。"""
    return Node(id=nid, title=kw.pop("title", nid),
                requires=list(requires or []), **kw)


# ---------------------------------------------------------------------------
# 真实数据
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def shipped():
    return load_nodes()


def test_shipped_data_is_valid(shipped):
    """包内自带的路径数据必须自身无错。"""
    issues = graph.validate(shipped)
    assert issues == [], "path.yaml 存在问题：\n" + "\n".join(issues)


def test_shipped_data_has_multiple_entries(shipped):
    """应当有多个入口节点（说明不是线性清单）。"""
    entries = [n.id for n in shipped if n.is_entry]
    assert len(entries) >= 2


def test_shipped_data_has_branching(shipped):
    """应当存在「一个节点解锁多个后继」的分叉，否则用不上图引擎。"""
    fan_out = {n.id: 0 for n in shipped}
    for node in shipped:
        for dep in node.requires:
            fan_out[dep] = fan_out.get(dep, 0) + 1
    assert max(fan_out.values()) >= 2


def test_shipped_data_has_node_with_multiple_requires(shipped):
    """应当存在「需要多个前置」的汇聚节点。"""
    assert any(len(n.requires) >= 2 for n in shipped)


def test_topological_order_covers_all(shipped):
    order = graph.topological_order(shipped)
    assert len(order) == len(shipped)


def test_topological_order_respects_dependencies(shipped):
    order = graph.topological_order(shipped)
    pos = {nid: i for i, nid in enumerate(order)}
    for node in shipped:
        for dep in node.requires:
            assert pos[dep] < pos[node.id], (
                f"{dep} 应当排在 {node.id} 之前"
            )


# ---------------------------------------------------------------------------
# 环检测
# ---------------------------------------------------------------------------

def test_find_cycles_empty_for_dag():
    nodes = [make("a"), make("b", ["a"]), make("c", ["b"])]
    assert graph.find_cycles(nodes) == []


def test_find_cycles_detects_two_node_cycle():
    nodes = [make("a", ["b"]), make("b", ["a"])]
    cycles = graph.find_cycles(nodes)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b"}


def test_find_cycles_detects_three_node_cycle():
    nodes = [make("a", ["c"]), make("b", ["a"]), make("c", ["b"])]
    cycles = graph.find_cycles(nodes)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def test_validate_reports_cycle():
    nodes = [make("a", ["b"]), make("b", ["a"])]
    issues = graph.validate(nodes)
    assert any("循环依赖" in i for i in issues)


def test_topological_order_incomplete_when_cycle_exists():
    """有环时，被卷入的节点不应出现在拓扑序里。"""
    nodes = [make("ok"), make("a", ["b"]), make("b", ["a"])]
    order = graph.topological_order(nodes)
    assert order == ["ok"]


# ---------------------------------------------------------------------------
# 其他校验
# ---------------------------------------------------------------------------

def test_validate_reports_dangling_reference():
    nodes = [make("a"), make("b", ["nope"])]
    issues = graph.validate(nodes)
    assert any("前置" in i and "nope" in i for i in issues)


def test_validate_reports_self_reference():
    nodes = [make("a", ["a"])]
    issues = graph.validate(nodes)
    assert any("自己" in i for i in issues)


def test_validate_reports_isolated_node():
    nodes = [make("a"), make("b", ["a"]), make("lonely")]
    issues = graph.validate(nodes)
    assert any("lonely" in i for i in issues)


def test_single_node_is_not_isolated():
    """只有一个节点时不应报孤立——那只是数据量小。"""
    assert graph.validate([make("solo")]) == []


# ---------------------------------------------------------------------------
# 求解
# ---------------------------------------------------------------------------

def test_unlocked_returns_entries_initially():
    nodes = [make("a"), make("b"), make("c", ["a"])]
    assert set(graph.unlocked(nodes, set())) == {"a", "b"}


def test_unlocked_after_completing():
    nodes = [make("a"), make("b"), make("c", ["a"])]
    assert set(graph.unlocked(nodes, {"a"})) == {"b", "c"}


def test_unlocked_requires_all_prerequisites():
    """多前置节点必须在全部前置完成之后才解锁。"""
    nodes = [make("a"), make("b"), make("c", ["a", "b"])]
    assert "c" not in graph.unlocked(nodes, {"a"})
    assert "c" in graph.unlocked(nodes, {"a", "b"})


def test_blocked_lists_missing_prerequisites():
    nodes = [make("a"), make("b"), make("c", ["a", "b"])]
    assert graph.blocked(nodes, set()) == {"c": ["a", "b"]}
    assert graph.blocked(nodes, {"a"}) == {"c": ["b"]}


def test_blocked_excludes_completed():
    nodes = [make("a"), make("b", ["a"])]
    assert graph.blocked(nodes, {"a", "b"}) == {}


# ---------------------------------------------------------------------------
# 路径规划
# ---------------------------------------------------------------------------

def test_plan_returns_ordered_steps():
    nodes = [
        make("a"), make("b", ["a"]),
        make("c", ["b"]), make("d"),
    ]
    assert graph.plan(nodes, "c") == ["a", "b", "c"]


def test_plan_skips_completed_nodes():
    nodes = [make("a"), make("b", ["a"]), make("c", ["b"])]
    assert graph.plan(nodes, "c", {"a"}) == ["b", "c"]


def test_plan_empty_when_prerequisites_done():
    nodes = [make("a"), make("b", ["a"])]
    assert graph.plan(nodes, "b", {"a"}) == ["b"]


def test_plan_handles_diamond_dependency():
    """菱形依赖：a → (b, c) → d，两条路都必须在 d 之前。"""
    nodes = [
        make("a"), make("b", ["a"]),
        make("c", ["a"]), make("d", ["b", "c"]),
    ]
    steps = graph.plan(nodes, "d")
    assert steps[0] == "a" and steps[-1] == "d"
    assert set(steps) == {"a", "b", "c", "d"}


def test_plan_unknown_target_raises():
    with pytest.raises(KeyError):
        graph.plan([make("a")], "nope")


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

def test_completion_ratio():
    nodes = [make("a"), make("b"), make("c", ["a"])]
    assert graph.completion(nodes, set()) == 0.0
    assert graph.completion(nodes, {"a"}) == pytest.approx(1 / 3)
    assert graph.completion(nodes, {"a", "b", "c"}) == 1.0


def test_completion_ignores_unknown_ids():
    nodes = [make("a"), make("b")]
    assert graph.completion(nodes, {"a", "不存在"}) == 0.5


def test_completion_of_empty_path():
    assert graph.completion([], set()) == 0.0


def test_stage_summary_groups_by_stage():
    nodes = [
        make("a", stage="第一段"),
        make("b", stage="第一段", requires=["a"]),
        make("c", stage="第二段", requires=["b"]),
    ]
    summary = graph.stage_summary(nodes, {"a"})
    assert summary == [("第一段", 1, 2), ("第二段", 0, 1)]
