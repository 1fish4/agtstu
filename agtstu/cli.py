"""命令行界面。

    agtstu check              校验路径数据是否有错
    agtstu list               按学习顺序列出全部节点
    agtstu next               我下一步能学什么
    agtstu show <id>          查看某个节点的详情
    agtstu path <id>          达成某个目标需要走的路
    agtstu done <id>          标记某节点为已完成
    agtstu undo <id>          取消完成标记
    agtstu stats              进度统计
"""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

from . import graph, progress
from .console import enable_utf8
from .loader import load_nodes
from .model import Node

#: 终端标记。
MARK_DONE = "✓"
MARK_OPEN = "○"
MARK_LOCK = "·"


def _disp_width(text: str) -> int:
    """字符串的**显示宽度**：中日韩全角字符占 2 列，其余占 1 列。

    直接用 f-string 的 ``:<20`` 补空格会错位——它按字符数算，
    而「函数」两个字在终端里占 4 列。这里按真实列宽计算。
    """
    return sum(
        2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in text
    )


def _pad(text: str, width: int) -> str:
    """按显示宽度右补空格。"""
    return text + " " * max(0, width - _disp_width(text))


def _status(node: Node, done: set[str], open_ids: set[str]) -> tuple[str, str]:
    """返回 ``(标记, 状态说明)``。"""
    if node.id in done:
        return MARK_DONE, "已完成"
    if node.id in open_ids:
        return MARK_OPEN, "可学"
    missing = [d for d in node.requires if d not in done]
    return MARK_LOCK, "缺 " + "、".join(missing)


def _load(args) -> list[Node]:
    return load_nodes(args.data)


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def cmd_check(args) -> int:
    """校验路径数据。"""
    nodes = _load(args)
    issues = graph.validate(nodes)

    if not issues:
        print(f"✓ 校验通过：{len(nodes)} 个节点，依赖关系完整，无循环依赖。")
        return 0

    print(f"✗ 发现 {len(issues)} 个问题：\n")
    for issue in issues:
        print("  -", issue)
    return 1


def cmd_list(args) -> int:
    """按学习顺序列出全部节点。"""
    nodes = _load(args)
    index = graph.build_index(nodes)
    done = progress.load()
    open_ids = set(graph.unlocked(nodes, done))

    order = graph.topological_order(nodes)
    if len(order) < len(nodes):
        print("⚠ 存在循环依赖，部分节点无法排序。请先运行 `agtstu check`。\n")

    id_width = max((_disp_width(n) for n in order), default=0)
    title_width = max((_disp_width(index[n].title) for n in order), default=0)
    current_stage = None

    for nid in order:
        node = index[nid]
        if node.stage and node.stage != current_stage:
            current_stage = node.stage
            print(f"\n【{current_stage}】")
        mark, note = _status(node, done, open_ids)
        print(f"  {mark} {_pad(nid, id_width)}  "
              f"{_pad(node.title, title_width)}  {note}")

    total = len(nodes)
    finished = len(set(order) & done)
    print(f"\n进度：{finished}/{total}（{graph.completion(nodes, done):.0%}）")
    return 0


def cmd_next(args) -> int:
    """列出当前可以学的节点。"""
    nodes = _load(args)
    done = progress.load()
    open_ids = graph.unlocked(nodes, done)

    if not open_ids:
        remaining = len(nodes) - len(set(n.id for n in nodes) & done)
        if remaining == 0:
            print("🎉 全部节点已完成。")
        else:
            print("当前没有可学的节点——依赖关系可能有环，请运行 `agtstu check`。")
        return 0

    index = graph.build_index(nodes)
    print(f"现在可以学（{len(open_ids)} 个）：\n")
    for nid in open_ids:
        node = index[nid]
        print(f"  ○ {nid}  —  {node.title}")
        titles = node.topic_titles
        if titles:
            print(f"      知识点：{'、'.join(titles[:3])}"
                  + ("…" if len(titles) > 3 else ""))
    print("\n随便挑一个开始即可，顺序不影响。用 `agtstu show <id>` 看详情。")
    return 0


def cmd_show(args) -> int:
    """显示单个节点的详情。"""
    nodes = _load(args)
    index = graph.build_index(nodes)
    if args.id not in index:
        print(f"✗ 没有这个节点：{args.id}")
        print("  用 `agtstu list` 查看全部节点 id。")
        return 1

    node = index[args.id]
    done = progress.load()
    open_ids = set(graph.unlocked(nodes, done))
    mark, note = _status(node, done, open_ids)

    print(f"{mark} {node.title}  ({node.id})   状态：{note}")
    if node.stage:
        print(f"阶段：{node.stage}")
    if node.summary:
        print(f"\n{node.summary}")

    def section(title: str, items: list[str]) -> None:
        if items:
            print(f"\n{title}")
            for it in items:
                print(f"  - {it}")

    if node.requires:
        print("\n前置：" + "、".join(node.requires))

    section("要掌握的知识点", node.topic_titles)
    section("验收标准", node.acceptance)

    if node.project:
        print("\n参考项目：" + node.project.name)
        if node.project.repo:
            print("  出处：" + node.project.repo)
        if node.project.note:
            print("  说明：" + node.project.note)

    if node.pitfalls:
        print("\n常见坑（作者踩过的）")
        for p in node.pitfalls:
            head = (p.text or p.symptom or "").strip().splitlines()
            print(f"  - {head[0] if head else ''}")

    if node.resources:
        print("\n延伸资源")
        for r in node.resources:
            print(f"  - {r.title}  {r.url}")
            if r.note:
                print(f"      {r.note}")

    if node.id not in done:
        print(f"\n完成后执行：agtstu done {node.id}")
    return 0


def cmd_path(args) -> int:
    """给出达成目标的学习路径。"""
    nodes = _load(args)
    index = graph.build_index(nodes)
    if args.id not in index:
        print(f"✗ 没有这个节点：{args.id}")
        return 1

    done = progress.load()
    steps = graph.plan(nodes, args.id, done)

    target = index[args.id]
    if not steps:
        print(f"目标「{target.title}」的前置已全部完成，可以直接开始。")
        return 0

    print(f"达成「{target.title}」还需要 {len(steps)} 步：\n")
    for i, nid in enumerate(steps, 1):
        node = index[nid]
        tag = "  ← 目标" if nid == args.id else ""
        print(f"  {i:>2}. {node.title}  ({nid}){tag}")
    print("\n执行 `agtstu done <id>` 逐个标记完成。")
    return 0


def cmd_done(args) -> int:
    """标记节点为已完成。"""
    nodes = _load(args)
    index = graph.build_index(nodes)
    if args.id not in index:
        print(f"✗ 没有这个节点：{args.id}")
        return 1

    node = index[args.id]
    done = progress.load()

    # 检查前置是否都已完成——只提醒，不阻拦
    missing = [d for d in node.requires if d not in done]
    if missing:
        titles = [index[m].title if m in index else m for m in missing]
        print(f"⚠ 还有前置未完成：{'、'.join(titles)}")
        print("  （仅提醒，仍会记录。前置没打牢后面会更吃力。）")

    progress.mark(args.id)
    done = progress.load()
    print(f"✓ 已标记完成：{node.title}")
    print(f"  进度：{len(set(index) & done)}/{len(nodes)}"
          f"（{graph.completion(nodes, done):.0%}）")
    return 0


def cmd_undo(args) -> int:
    """取消完成标记。"""
    progress.unmark(args.id)
    print(f"✓ 已取消完成标记：{args.id}")
    return 0


def cmd_stats(args) -> int:
    """按阶段汇总进度。"""
    nodes = _load(args)
    done = progress.load()

    print("按阶段统计：\n")
    summary = graph.stage_summary(nodes, done)
    name_width = max((_disp_width(n) for n, _, _ in summary), default=0)

    for name, finished, total in summary:
        bar_len = 20
        filled = int(bar_len * finished / total) if total else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  {_pad(name, name_width)}  {bar}  {finished}/{total}")

    print(f"\n总体：{graph.completion(nodes, done):.0%}")

    open_ids = graph.unlocked(nodes, done)
    if open_ids:
        print(f"接下来可学 {len(open_ids)} 个：{'、'.join(open_ids)}")
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agtstu",
        description="AgtStu —— 把学习路径当作依赖图来管理的开源学习工具",
    )
    parser.add_argument(
        "--data", type=Path, default=None,
        help="指定路径数据文件（默认使用包内的 data/path.yaml）",
    )

    sub = parser.add_subparsers(dest="command", metavar="<命令>")

    sub.add_parser("check", help="校验路径数据").set_defaults(func=cmd_check)
    sub.add_parser("list", help="按学习顺序列出全部节点").set_defaults(func=cmd_list)
    sub.add_parser("next", help="我下一步能学什么").set_defaults(func=cmd_next)
    sub.add_parser("stats", help="按阶段汇总进度").set_defaults(func=cmd_stats)

    p_show = sub.add_parser("show", help="查看节点详情")
    p_show.add_argument("id", help="节点 id")
    p_show.set_defaults(func=cmd_show)

    p_path = sub.add_parser("path", help="达成目标的学习路径")
    p_path.add_argument("id", help="目标节点 id")
    p_path.set_defaults(func=cmd_path)

    p_done = sub.add_parser("done", help="标记节点为已完成")
    p_done.add_argument("id", help="节点 id")
    p_done.set_defaults(func=cmd_done)

    p_undo = sub.add_parser("undo", help="取消完成标记")
    p_undo.add_argument("id", help="节点 id")
    p_undo.set_defaults(func=cmd_undo)

    return parser


def main(argv: list[str] | None = None) -> int:
    # 英文 Windows 的默认输出编码是 cp1252，打印中文会直接抛异常。
    # 入口处统一切到 UTF-8。
    enable_utf8()

    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
