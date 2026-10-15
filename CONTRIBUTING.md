# 贡献指南

感谢愿意为 AgtStu 出力。最受欢迎的贡献是**补充学习路径节点** —— 尤其是你踩过的坑。

## 开发环境

```bash
git clone https://github.com/1fish4/agtstu.git
cd agtstu
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -e ".[dev]"
pytest
```

提交 PR 前请确保测试全部通过，并且 `agtstu check` 没有报错。

---

## 贡献学习路径节点（最需要）

路径数据在 `agtstu/data/path.yaml`。新增节点请遵循下面的格式。

### 完整示例

```yaml
- id: py_func                      # 必填。英文唯一标识，供依赖引用
  title: 函数                      # 必填。中文显示名
  stage: 阶段一 · Python 与工程基础  # 所属阶段，用于分组
  requires: [py_flow, py_container] # 必填。前置节点 id 列表；入口节点写 []
  skills:                          # 本节点要掌握的知识点
    - 定义与调用、参数与返回值
    - 作用域与 LEGB 规则
  acceptance:                      # 验收标准，逐条自评
    - 能把一段重复代码抽成函数
    - 能写出带类型注解和 docstring 的函数
  project:                         # 配套参考项目
    name: 把猜数字改造成函数版
    note: 拆成生成答案、判断猜测、统计次数几个函数
    repo: ""                       # 若指向他人仓库，必须填出处
  pitfalls:                        # 常见坑 —— 这部分最有价值
    - 默认参数不要用可变对象，会跨调用累积
    - 函数名要有动词，func1 这种名字一周后自己都看不懂
  resources:                       # 延伸资源，只放链接
    - title: Python 官方教程
      url: https://docs.python.org/zh-cn/3/tutorial/
      note: 函数那一章
```

### 必填字段

只有三个：`id`、`title`、`requires`。其余可选，但**强烈建议补全**。

### 写 `pitfalls` 的几条要求

这是本项目区别于普通资料的核心，请认真写：

1. **必须是你真实踩过或真实见过的**，不要从教程里抄
2. **说清楚「错在哪」和「为什么」**，不要只写「注意不要写错」
3. 越具体越好 —— 「遍历列表时删除元素会漏掉元素」比「注意列表操作」有用一百倍

反例（不要这样写）：

```yaml
pitfalls:
  - 注意语法
  - 小心出错
```

正例：

```yaml
pitfalls:
  - 遍历列表时删除元素会漏掉元素 —— 要遍历副本或倒序删
  - dict 的键必须可哈希，list 不能当键
```

### 写 `acceptance` 的几条要求

1. **可自评** —— 读完能明确判断「我做到了没有」
2. **不设标准答案** —— 写「能写出一个接收输入、转换、输出的脚本」，
   而不是「必须用 f-string 实现」
3. 3~5 条为宜

### 改完必须验证

```bash
agtstu check
```

会检查：悬空引用、自依赖、孤立节点、循环依赖。
**循环依赖尤其要注意** —— 一旦 A 依赖 B、B 又依赖 A，两个节点就永远解锁不了。

---

## 贡献代码

### 核心设计约束

1. **数据与代码分离** —— 改路径内容不应该需要动 Python 代码
2. **引擎不依赖具体内容** —— `graph.py` 只认节点和依赖关系，不关心学的是什么
3. **测试优先** —— 新增算法或修复 bug，都请补测试

### 提 PR

1. 从 `main` 切出分支：`git checkout -b feat/your-feature`
2. 一个提交解决一件事，提交信息写清做了什么
3. 跑 `pytest` 确认通过

### 提 Issue

- **数据错误** —— 依赖关系写错、验收标准不清晰、坑描述不准
- **功能建议** —— 说明使用场景，而不只是想要什么函数
- **Bug** —— 附上 Python 版本与最小复现代码

---

## 关于收录他人项目

**只收录链接，不转载内容。** 若节点的 `project.repo` 指向他人仓库：

| 原项目许可证 | 能否转载其内容 |
|------------|:---:|
| MIT / Apache-2.0 / BSD | 可以，但必须保留版权声明与许可证文本 |
| GPL / AGPL | 谨慎，有传染性 |
| 没有 LICENSE 文件 | **不可以** |

默认姿态：给链接 + 写你自己的实践记录。

## 许可证

贡献的代码与内容将按项目的 [MIT License](LICENSE) 发布。
