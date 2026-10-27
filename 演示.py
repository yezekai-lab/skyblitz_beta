"""演示用：把游戏摆到"一眼能看到进化卡"的状态。

⚠️ 这个文件不属于游戏内容，只是现场演示时省时间的工具。
游戏本体（alien_invasion.py 等）完全不知道它的存在。

为什么需要它：进化卡出现的条件是「两条相关升级都拿满」，
正常玩要打十几分钟才凑得出来 —— 而演示只有 3 分钟。

用法（在 alien_invasion 目录下）：

    python 演示.py           # 一开局就弹出含 STARFALL CANNON 的三选一
    python 演示.py --boss    # 换成含 VOID LANCE 的三选一
"""

import sys

import pygame

from alien_invasion import AlienInvasion
from game_state import State
from upgrade_screen import UpgradeScreen

# 两条进化路径，以及各自需要先满级的那两条前置
PATHS = {
    "starfall": (("multi_shot", "cannon"), "starfall_cannon"),
    "boss": (("pierce", "psionic_storm"), "void_lance"),
}


def build_demo(path="starfall"):
    """造一局已经满足进化条件的游戏，并把三选一界面直接摆出来。

    返回 (game, 选中的那张进化卡)。调用方接着跑 `game.run_game()` 就行。

    用的是真实的升级/抽卡/界面代码 —— 只是把"前置先给满"
    和"直接把界面摆出来"这两步替你做了。
    """
    required_keys, evolve_key = PATHS[path]

    game = AlienInvasion()
    game._start_game()

    # ① 把两条前置直接拉满（走的是真实的 take()，效果真的生效了）
    for key in required_keys:
        upgrade = game.upgrades.find(key)
        for _ in range(upgrade.max_level):
            game.upgrades.take(key)

    # ② 摆出三选一：进化卡 + 两张普通卡（挑两条最直观的做陪衬）
    evolve = game.upgrades.find(evolve_key)
    others = [game.upgrades.find(k) for k in ("engine", "magazine")]
    game.upgrade_screen = UpgradeScreen([evolve] + others, game.screen_rect)
    game.state = State.UPGRADING
    pygame.mouse.set_visible(True)

    # ③ 让 HUD 反映出"前置已拿满"
    game.sb.prep_upgrades()
    game.sb.prep_score_and_next()

    return game, evolve


def main():
    path = "boss" if "--boss" in sys.argv else "starfall"
    game, evolve = build_demo(path)
    print(f"演示模式：三选一里第 1 张 = {evolve.title}（按 1 选它）")
    game.run_game()


if __name__ == "__main__":
    main()
