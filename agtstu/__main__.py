"""让 ``python -m agtstu`` 等价于 ``agtstu`` 命令。"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
