"""掌握程度（mastery）的解析与数据完整性测试。

``mastery`` 回答的是「学到哪算够」，它的价值不在字段本身，
而在**每个节点都写满了**——空着的字段等于没有约束。
所以这里除了测解析，还要守住内容的完整性。
"""

from __future__ import annotations

import pytest

from agtstu.loader import load_nodes
from agtstu.model import MASTERY_TIERS, Mastery, from_dict


def _minimal(**extra):
    """构造一个通过必填校验的最小节点字典。"""
    raw = {"id": "x", "title": "示例", "requires": []}
    raw.update(extra)
    return raw


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

def test_missing_mastery_is_none():
    node = from_dict(_minimal())
    assert node.mastery is None


def test_short_form_accepts_tier_string():
    """支持 mastery: 会用 这种简写。"""
    node = from_dict(_minimal(mastery="会用"))
    assert node.mastery is not None
    assert node.mastery.tier == "会用"
    assert node.mastery.must == ""


def test_full_form_parses_all_fields():
    node = from_dict(_minimal(mastery={
        "tier": "熟练",
        "must": "能独立写出来",
        "enough": "报错能自己定位",
        "beyond": "底层实现不用管",
    }))
    assert node.mastery.tier == "熟练"
    assert node.mastery.must == "能独立写出来"
    assert node.mastery.enough == "报错能自己定位"
    assert node.mastery.beyond == "底层实现不用管"
    assert node.mastery.filled is True


def test_unknown_tier_rejected():
    with pytest.raises(ValueError, match="mastery"):
        from_dict(_minimal(mastery="精通"))


def test_unknown_tier_rejected_in_full_form():
    with pytest.raises(ValueError, match="mastery.tier"):
        from_dict(_minimal(mastery={"tier": "入门"}))


def test_wrong_type_rejected():
    with pytest.raises(ValueError, match="mastery"):
        from_dict(_minimal(mastery=["会用"]))


def test_empty_mastery_is_not_filled():
    m = Mastery()
    assert m.filled is False


# ---------------------------------------------------------------------------
# 随附数据的完整性
# ---------------------------------------------------------------------------

def test_shipped_nodes_all_have_mastery():
    """每个节点都必须标注掌握程度——这是「学到哪算够」的前提。"""
    missing = [n.id for n in load_nodes() if not (n.mastery and n.mastery.tier)]
    assert not missing, f"这些节点没有标注掌握程度：{missing}"


def test_shipped_mastery_tiers_are_valid():
    bad = [
        (n.id, n.mastery.tier)
        for n in load_nodes()
        if n.mastery and n.mastery.tier not in MASTERY_TIERS
    ]
    assert not bad, f"档位不合法：{bad}"


def test_shipped_mastery_fields_are_complete():
    """三档说明必须都写。空着的 ``beyond`` 等于没有免除焦虑的边界。"""
    incomplete = []
    for node in load_nodes():
        m = node.mastery
        if not m:
            continue
        for name in ("must", "enough", "beyond"):
            if not getattr(m, name).strip():
                incomplete.append(f"{node.id}.{name}")
    assert not incomplete, f"这些字段为空：{incomplete}"


def test_shipped_mastery_tier_coverage():
    """三档都应被用到——只标一种说明分级没有真正起作用。"""
    tiers = {n.mastery.tier for n in load_nodes() if n.mastery}
    assert len(tiers) >= 2, f"只用到 {tiers}，分级意义不大"
