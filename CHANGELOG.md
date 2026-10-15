# 更新日志

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### 计划中

- 静态展示页（把路径数据渲染成 HTML）
- GitHub Actions 自动测试
- 贡献指南与节点数据格式说明
- 阶段二内容（后端基础）

---

## [0.1.0] - 2026-10-15

首个可用版本：路径引擎与命令行界面。

### 新增

- **数据模型** `model.py`：定义学习路径中的「节点」。
  包含知识点、验收标准、参考项目、常见坑、延伸资源五类内容字段。
- **加载器** `loader.py`：从 YAML 读取路径数据，支持单前置简写与字段校验。
- **依赖图引擎** `graph.py`（核心）：
  - `validate()` 校验悬空引用、自依赖、孤立节点、循环依赖
  - `find_cycles()` DFS 三色标记环检测
  - `topological_order()` Kahn 拓扑排序，同层按文件顺序稳定输出
  - `unlocked()` / `blocked()` 计算拓扑前沿与缺失前置
  - `plan()` 由祖先集合计算达成目标所需的完整路径
  - `completion()` / `stage_summary()` 进度统计
- **进度模块** `progress.py`：进度存于用户目录，不随项目变动丢失。
- **命令行** `cli.py`：`check` / `list` / `next` / `show` / `path` /
  `done` / `undo` / `stats` 八个子命令。
- **路径内容** `data/path.yaml`：阶段一「Python 与工程基础」共 15 个节点，
  覆盖环境搭建、语法基础、代码组织、工程入门四个层次。
- **测试**：40 项，含对真实数据的完整性校验与对合成小图的算法验证。

### 说明

- 依赖仅 `pyyaml`，运行时无其他第三方库
- 路径数据与引擎代码分离，改内容不需要动代码
- 中文表格对齐：命令行输出按**显示宽度**补空格，而非字符数

[Unreleased]: https://github.com/1fish4/agtstu/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/1fish4/agtstu/releases/tag/v0.1.0
