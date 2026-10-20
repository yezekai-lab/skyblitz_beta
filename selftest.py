"""一次跑完所有自测。用法（在 alien_invasion 目录下）：

    python selftest.py

所有脚本都是「无头」运行的 —— 不会弹出游戏窗口，可以直接在任何时候跑。
每加一个新功能，都应该先跑一遍这个，确认没把原来的东西改坏。
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    ("核心功能回归", "selftest_core.py"),
    ("输入层", "selftest_input.py"),
    ("端到端主循环", "selftest_e2e.py"),
    ("升级池", "selftest_upgrades.py"),
    ("三选一界面", "selftest_ui.py"),
]


def main():
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", PYTHONUTF8="1")
    failed = []
    for title, filename in SUITES:
        print()
        print("#" * 66)
        print(f"# {title}  ({filename})")
        print("#" * 66)
        result = subprocess.run(
            [sys.executable, os.path.join(HERE, filename)], cwd=HERE, env=env
        )
        if result.returncode != 0:
            failed.append(title)

    print()
    print("=" * 66)
    if failed:
        print(f"有失败的测试套: {'、'.join(failed)}")
    else:
        print("全部通过 ✅")
    print("=" * 66)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
