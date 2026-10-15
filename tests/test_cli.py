"""命令行辅助函数的测试。

重点验证**中文对齐**：终端里汉字占两列，用 f-string 的字符数补空格会错位。
"""

from __future__ import annotations

import pytest

from agtstu.cli import _disp_width, _pad, build_parser, main


# ---------------------------------------------------------------------------
# 显示宽度
# ---------------------------------------------------------------------------

def test_ascii_width_equals_length():
    assert _disp_width("abc") == 3
    assert _disp_width("") == 0


def test_cjk_counts_as_two_columns():
    assert _disp_width("函数") == 4
    assert _disp_width("阶段一") == 6


def test_mixed_width():
    assert _disp_width("py_函数") == 7      # 3 + 2*2


def test_pad_aligns_cjk_and_ascii():
    """两种写法补到同一宽度后，显示列宽必须一致。"""
    a = _pad("函数", 8)
    b = _pad("abcdefgh", 8)
    assert _disp_width(a) == _disp_width(b) == 8


def test_pad_never_truncates():
    assert _pad("这是一个很长的中文标题", 4) == "这是一个很长的中文标题"


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def test_parser_has_all_commands():
    parser = build_parser()
    actions = [
        a for a in parser._actions
        if hasattr(a, "choices") and a.choices
    ]
    commands = set()
    for a in actions:
        commands |= set(a.choices)
    assert {"check", "list", "next", "show", "path",
            "done", "undo", "stats"} <= commands


def test_main_without_command_prints_help(capsys):
    assert main([]) == 0
    assert "agtstu" in capsys.readouterr().out


def test_main_check_passes_on_shipped_data(capsys):
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    assert "校验通过" in out


def test_main_show_unknown_node_fails(capsys):
    assert main(["show", "不存在的节点"]) == 1
    assert "没有这个节点" in capsys.readouterr().out


def test_main_list_runs(capsys):
    assert main(["list"]) == 0
    assert "进度：" in capsys.readouterr().out


def test_main_path_unknown_node_fails(capsys):
    assert main(["path", "不存在的节点"]) == 1
