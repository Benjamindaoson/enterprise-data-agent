"""
iQuery - 智能数据分析平台

Usage:
    python -m src          # 启动命令行界面
    python -m src web      # 启动 Web 界面
"""

import sys


def main():
    """主入口"""
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        # 启动 Web 界面
        from src.web.server import run_web
        run_web()
    else:
        # 启动命令行界面
        from src.cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
