"""AgtStu —— 把学习路径当作依赖图来管理的开源学习工具。

核心理念
--------
学习路径不是一份线性清单，而是一张**有向无环图**：
一个知识点可以有多个前置，也能解锁多个后继。

    py_basic ──┬─> py_container ──┐
               │                  ├─> py_func ──> py_module
               └─> py_flow ───────┘

把这份关系写成数据，程序就能替你算出「现在能学什么」「还差什么」。

快速开始
--------
    >>> from agtstu import load_nodes, graph
    >>> nodes = load_nodes()
    >>> graph.validate(nodes)               # 校验数据
    []
    >>> graph.unlocked(nodes)               # 现在能学什么
    ['py_env', 'eng_git']
    >>> graph.plan(nodes, 'py_func')        # 达成目标要走的路
    ['py_env', 'py_basic', 'py_container', 'py_flow', 'py_func']

命令行
------
见 :mod:`agtstu.cli`，或直接运行 ``agtstu --help``。
"""

from __future__ import annotations

from . import graph, progress
from .loader import load_nodes
from .model import Node, Project, Resource

__version__ = "0.1.0"

__all__ = [
    "graph",
    "progress",
    "load_nodes",
    "Node",
    "Project",
    "Resource",
    "__version__",
]
