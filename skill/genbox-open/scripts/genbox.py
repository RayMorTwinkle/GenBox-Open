#!/usr/bin/env python3
"""从已安装的技能目录调用仓库内的开源客户端。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from genbox_open.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
