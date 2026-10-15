#!/usr/bin/env python3
"""把 ``path.yaml`` 编译成静态展示站（``docs/index.html``）。

用法::

    python tools/build_site.py

为什么需要这一步
----------------
GitHub Pages 只能托管**静态文件**，而学习路径本身是 YAML——浏览器读不了。
所以构建时把路径数据编译成 JSON，内嵌进 HTML。

产出是一个**单文件站点**：不依赖任何外部资源，双击能打开，
也能直接放到任意静态托管上。

编译的同时会跑一次数据校验（环 / 悬空引用 / 孤立节点）。
校验不通过就中止构建——**不让坏数据上线**。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agtstu import graph  # noqa: E402
from agtstu.console import enable_utf8  # noqa: E402
from agtstu.loader import load_nodes  # noqa: E402
from agtstu.model import Node  # noqa: E402

#: 测试数量与子命令数量。改动代码后请同步这两个数字。
TEST_COUNT = 40
COMMAND_COUNT = 8

TEMPLATE = Path(__file__).resolve().parent / "template.html"
OUT_DIR = ROOT / "docs"


def compute_levels(nodes: list[Node]) -> dict[str, int]:
    """按**最长路径**给每个节点定层级，用于分层布局。

    取最长路径而不是最短——这样所有前置都画在当前层之前，
    边永远朝下，图不会出现交叉回溯。
    """
    index = graph.build_index(nodes)
    level: dict[str, int] = {}
    for nid in graph.topological_order(nodes):
        deps = [d for d in index[nid].requires if d in index]
        level[nid] = 0 if not deps else max(level[d] for d in deps) + 1
    return level


def build_payload(nodes: list[Node]) -> dict:
    """组装前端需要的全部数据。"""
    index = graph.build_index(nodes)
    level = compute_levels(nodes)
    order = graph.topological_order(nodes)
    rank = {nid: i for i, nid in enumerate(order)}

    unlocks: dict[str, list[str]] = {n.id: [] for n in nodes}
    for node in nodes:
        for dep in node.requires:
            unlocks.setdefault(dep, []).append(node.id)

    items = []
    for node in nodes:
        items.append({
            "id": node.id,
            "title": node.title,
            "stage": node.stage,
            "level": level[node.id],
            "rank": rank.get(node.id, 0),
            "requires": list(node.requires),
            "unlocks": unlocks[node.id],
            "skills": list(node.skills),
            "acceptance": list(node.acceptance),
            "pitfalls": list(node.pitfalls),
            "project": (
                {
                    "name": node.project.name,
                    "note": node.project.note,
                    "repo": node.project.repo,
                }
                if node.project
                else None
            ),
            "resources": [
                {"title": r.title, "url": r.url, "note": r.note}
                for r in node.resources
            ],
        })

    stages = [
        {"name": name, "total": total}
        for name, _done, total in graph.stage_summary(nodes)
    ]

    return {
        # 注意：这里**不能**写构建日期。产物必须由输入唯一决定，
        # 否则同一份数据每次构建都不一样，CI 就无法校验
        # 「提交的 index.html 是否与数据同步」。
        "stats": {
            "nodes": len(nodes),
            "edges": sum(len(n.requires) for n in nodes),
            "stages": len(stages),
            "tests": TEST_COUNT,
            "commands": COMMAND_COUNT,
        },
        "stages": stages,
        "nodes": items,
    }


def main() -> int:
    # 英文 Windows 的默认输出编码是 cp1252，打印中文会直接抛异常
    # （GitHub Actions 的 windows-latest 就是这种环境）。
    enable_utf8()

    nodes = load_nodes()

    issues = graph.validate(nodes)
    if issues:
        print("数据校验未通过，已中止构建：", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    data = build_payload(nodes)

    template = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # 防止数据里出现 </script> 提前闭合脚本标签
    blob = blob.replace("</", "<\\/")

    html = template.replace("/*__DATA__*/null", blob)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    # .nojekyll：告诉 GitHub Pages 不要用 Jekyll 处理这个目录
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

    size_kb = out.stat().st_size / 1024
    print(f"已生成 {out}  ({size_kb:.1f} KB)")
    print(f"  节点 {data['stats']['nodes']} 个 · 依赖边 {data['stats']['edges']} 条")
    print(f"  数据校验：通过（无环、无悬空引用、无孤立节点）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
