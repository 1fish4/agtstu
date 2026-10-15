"""终端编码处理。

**为什么需要这个模块**

Windows 的默认输出编码取决于系统区域设置：

- 中文 Windows：GBK —— 能编码中文，所以问题不会暴露
- **英文 Windows：cp1252 —— 不能编码中文，一 print 就抛 UnicodeEncodeError**

后者正是 GitHub Actions 的 ``windows-latest`` 运行器。而本项目的所有输出
（命令行提示、构建日志）都是中文，所以必须显式把标准流切成 UTF-8，
否则 CLI 和构建脚本在英文 Windows 上会直接崩掉。

集中在这里处理，避免每个入口各写一遍。
"""

from __future__ import annotations

import sys

__all__ = ["enable_utf8"]


def enable_utf8() -> None:
    """把标准输出与标准错误切到 UTF-8。

    不是所有流都支持 ``reconfigure``（例如被重定向成普通文件对象时），
    遇到不支持的情况就静默跳过 —— 能切就切，切不了也不该因此崩溃。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass
